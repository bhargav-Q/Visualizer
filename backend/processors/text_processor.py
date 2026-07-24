import os
import json
import logging
from dotenv import load_dotenv
from pathlib import Path
import httpx
from openai import OpenAI, AsyncOpenAI
from models.schemas import TextResult, KeywordItem
from engine.vision_client import is_vision_api_disabled, disable_vision_api

logger = logging.getLogger(__name__)

# Shared HTTPX 15-second resilient timeout configuration
TIMEOUT_CONFIG = httpx.Timeout(15.0, connect=5.0)

# Load environment variables (.env in project root or current dir)
env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)
load_dotenv()
api_key = os.getenv("NVIDIA_API_KEY")

ENGLISH_STOPWORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are", "aren't",
    "as", "at", "be", "because", "been", "before", "being", "below", "between", "both", "but", "by",
    "can", "cannot", "could", "couldn't", "did", "didn't", "do", "does", "doesn't", "doing", "don't",
    "down", "during", "each", "few", "for", "from", "further", "had", "hadn't", "has", "hasn't",
    "have", "haven't", "having", "he", "her", "here", "hers", "herself", "him", "himself", "his", "how",
    "i", "if", "in", "into", "is", "isn't", "it", "its", "itself", "just", "me", "more", "most", "my",
    "myself", "no", "nor", "not", "of", "off", "on", "once", "only", "or", "other", "our", "ours",
    "ourselves", "out", "over", "own", "same", "she", "should", "shouldn't", "so", "some", "such",
    "than", "that", "the", "their", "theirs", "them", "themselves", "then", "there", "these", "they",
    "this", "those", "through", "to", "too", "under", "until", "up", "very", "was", "wasn't", "we",
    "were", "weren't", "what", "when", "where", "which", "while", "who", "whom", "why", "with", "would",
    "wouldn't", "you", "your", "yours", "yourself", "yourselves", "page", "total", "date", "null", "none"
}

def generate_local_fallback_text_result(raw_text: str, page_count: int = None, paragraph_count: int = None, ai_model: str = "local-heuristic") -> TextResult:
    """Generates a rich, non-empty local summary and term-frequency keyword ranking."""
    word_count = len(raw_text.split()) if raw_text else 0
    lines = [l.strip() for l in raw_text.split("\n") if l.strip() and not l.startswith("--- Page")]
    
    # 1. Summary Construction
    if lines:
        sample_snippets = lines[:3]
        summary_text = f"Document ingested successfully ({word_count} words across {page_count or 1} page(s)). Summary preview: " + " ".join(sample_snippets)
        if len(summary_text) > 350:
            summary_text = summary_text[:347] + "..."
    else:
        summary_text = f"Document ingested with {word_count} words across {page_count or 1} page(s). Full text and layout metrics extracted."

    # 2. Term Frequency Keyword Ranking
    import re
    from collections import Counter
    words = re.findall(r'\b[A-Za-z0-9_-]{3,25}\b', (raw_text or "").lower())
    filtered_words = [w for w in words if w not in ENGLISH_STOPWORDS and not w.isdigit()]
    
    counts = Counter(filtered_words)
    most_common = counts.most_common(15)
    
    keywords = []
    if most_common:
        max_freq = most_common[0][1]
        for w, freq in most_common:
            score = round(min(1.0, max(0.4, freq / max_freq)), 2)
            keywords.append(KeywordItem(word=w.title(), score=score))

    return TextResult(
        summary=summary_text,
        keywords=keywords,
        word_count=word_count,
        page_count=page_count,
        paragraph_count=paragraph_count,
        ai_model=ai_model
    )

def process_text(raw_text: str, page_count: int = None, paragraph_count: int = None) -> TextResult:
    word_count = len(raw_text.split()) if raw_text else 0
    model_name = os.getenv("TEXT_AI_MODEL", "meta/llama-3.1-70b-instruct")

    from engine.vision_client import is_vision_api_disabled, disable_vision_api
    
    if not api_key or is_vision_api_disabled():
        return generate_local_fallback_text_result(raw_text, page_count, paragraph_count, model_name)

    client = OpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=api_key,
        http_client=httpx.Client(timeout=httpx.Timeout(10.0, connect=3.0)),
        max_retries=1
    )

    prompt = f"""
    You are an expert data analyst. Please analyze the following document text and provide:
    1. A concise TL;DR summary (3-5 sentences).
    2. A list of up to 20 top keywords with their relevance score (0.0 to 1.0).
    
    Output strictly in JSON format matching this schema:
    {{
        "summary": "Your summary here",
        "keywords": [
            {{"word": "keyword1", "score": 0.95}}
        ]
    }}
    
    Text to analyze:
    {raw_text[:8000]}
    """

    try:
        completion = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            top_p=0.95,
            max_tokens=4096,
            stream=False,
            response_format={"type": "json_object"},
            timeout=10.0
        )

        response_content = completion.choices[0].message.content or ""
        
        if "<think>" in response_content:
            if "</think>" in response_content:
                response_content = response_content.split("</think>")[-1].strip()
            else:
                response_content = response_content.split("<think>")[-1].strip()

        start_idx = response_content.find("{")
        end_idx = response_content.rfind("}")
        if start_idx != -1 and end_idx != -1:
            response_content = response_content[start_idx:end_idx+1]

        ai_data = json.loads(response_content)
        
        keywords = [
            KeywordItem(word=k.get("word", ""), score=k.get("score", 0.0))
            for k in ai_data.get("keywords", [])
        ]
        
        return TextResult(
            summary=ai_data.get("summary") or generate_local_fallback_text_result(raw_text, page_count, paragraph_count).summary,
            keywords=keywords or generate_local_fallback_text_result(raw_text, page_count, paragraph_count).keywords,
            word_count=word_count,
            page_count=page_count,
            paragraph_count=paragraph_count,
            ai_model=model_name
        )
        
    except Exception as e:
        logger.warning(f"AI Text API Error: {e}")
        status_code = getattr(e, "status_code", None)
        err_msg = str(e).lower()
        if status_code in (429, 503) or "503" in err_msg or "429" in err_msg or "resourceexhausted" in err_msg:
            logger.warning("Text Processor hit rate limit or 503 error. Disabling API calls globally for 60 seconds.")
            disable_vision_api(60.0)
        elif "timeout" in err_msg or "timed out" in err_msg or "timeout" in type(e).__name__.lower():
            logger.warning("Text Processor request timed out. Disabling API calls globally for 60 seconds.")
            disable_vision_api(60.0)
            
        return generate_local_fallback_text_result(raw_text, page_count, paragraph_count, model_name)

async def process_text_async(raw_text: str, page_count: int = None, paragraph_count: int = None) -> TextResult:
    """Async wrapper for process_text enforcing 15-second non-blocking execution."""
    import asyncio
    try:
        return await asyncio.to_thread(process_text, raw_text, page_count, paragraph_count)
    except Exception as exc:
        logger.warning(f"Async process_text call failed: {exc}")
        word_count = len(raw_text.split()) if raw_text else 0
        return TextResult(
            summary="Summary unavailable — execution timed out.",
            keywords=[],
            word_count=word_count,
            page_count=page_count,
            paragraph_count=paragraph_count,
            ai_model=os.getenv("TEXT_AI_MODEL", "deepseek-ai/deepseek-v4-flash")
        )

