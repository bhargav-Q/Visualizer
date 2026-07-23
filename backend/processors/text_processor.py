import os
import json
from dotenv import load_dotenv
from pathlib import Path
from openai import OpenAI
from models.schemas import TextResult, KeywordItem

# Load environment variables (.env in project root or current dir)
env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)
load_dotenv()
api_key = os.getenv("NVIDIA_API_KEY")

def process_text(raw_text: str, page_count: int = None, paragraph_count: int = None) -> TextResult:
    word_count = len(raw_text.split())
    
    model_name = os.getenv("TEXT_AI_MODEL", "deepseek-ai/deepseek-v4-flash")


    fallback_summary = "Summary unavailable — AI service is temporarily down."
    fallback_keywords = []

    from engine.vision_client import is_vision_api_disabled, disable_vision_api
    
    if not api_key or is_vision_api_disabled():
        return TextResult(
            summary=fallback_summary,
            keywords=fallback_keywords,
            word_count=word_count,
            page_count=page_count,
            paragraph_count=paragraph_count,
            ai_model=model_name
        )

    client = OpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=api_key
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
    {raw_text[:8000]} # Limit text length to avoid token limits
    """

    try:
        completion = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            top_p=0.95,
            max_tokens=4096,
            extra_body={"chat_template_kwargs": {"thinking": False}},
            stream=False,
            response_format={"type": "json_object"},
            timeout=30.0
        )
        
        # Optional: Print reasoning if it exists (for debugging)
        reasoning = getattr(completion.choices[0].message, "reasoning", None) or getattr(completion.choices[0].message, "reasoning_content", None)
        if reasoning:
            print("AI Reasoning:", reasoning)

        response_content = completion.choices[0].message.content or ""
        
        # Strip DeepSeek AI <think>...</think> reasoning blocks if present
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
            summary=ai_data.get("summary", fallback_summary),
            keywords=keywords,
            word_count=word_count,
            page_count=page_count,
            paragraph_count=paragraph_count,
            ai_model=model_name
        )
        
    except Exception as e:
        print(f"AI API Error: {e}")
        status_code = getattr(e, "status_code", None)
        err_msg = str(e).lower()
        if status_code in (429, 503) or "503" in err_msg or "429" in err_msg or "resourceexhausted" in err_msg:
            logger.warning("Text Processor hit rate limit or 503 error. Disabling API calls globally for 60 seconds.")
            disable_vision_api(60.0)
        elif "timeout" in err_msg or "timed out" in err_msg or "timeout" in type(e).__name__.lower():
            logger.warning("Text Processor request timed out. Disabling API calls globally for 120 seconds.")
            disable_vision_api(120.0)
            
        return TextResult(
            summary=fallback_summary,
            keywords=fallback_keywords,
            word_count=word_count,
            page_count=page_count,
            paragraph_count=paragraph_count,
            ai_model=model_name
        )
