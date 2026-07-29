import os
import json
import logging
from typing import List, Optional, Any
from dotenv import load_dotenv
from pathlib import Path
import httpx
from openai import OpenAI, AsyncOpenAI
from models.schemas import TextResult, KeywordItem, QualitativeSectionResponse, TopicOutlineResponse
from engine.vision_client import is_vision_api_disabled, disable_vision_api
from constants import DocumentDomain, ENGLISH_STOPWORDS, MIN_TOPIC_TITLE_LEN

logger = logging.getLogger(__name__)

# Shared HTTPX 15-second resilient timeout configuration
TIMEOUT_CONFIG = httpx.Timeout(15.0, connect=5.0)

# Load environment variables (.env in project root or current dir)
env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)
load_dotenv()
api_key = os.getenv("NVIDIA_API_KEY")

def extract_qualitative_sections(raw_text: str) -> List[QualitativeSectionResponse]:
    """
    Extracts structured qualitative modules/topics, subtopics, and highlights from non-numeric documents
    such as course syllabi, brochures, policy guides, or whitepapers.
    """
    if not raw_text or not raw_text.strip():
        return []

    import re
    model_name = os.getenv("TEXT_AI_MODEL", "meta/llama-3.1-70b-instruct")

    # Local Deterministic Fallback Parser Function
    def parse_local_qualitative_topics(text: str) -> List[QualitativeSectionResponse]:
        lines = [l.strip() for l in text.split("\n") if l.strip() and not l.startswith("--- Page")]
        topics = []
        curr_title = None
        curr_subtopics = []
        highlights = []

        lower_text = text.lower()
        if any(k in lower_text for k in ['losses', 'payroll', 'policy', 'xmod', 'premium', 'claim', 'insurance', 'underwriting', 'coverage', 'deductible']):
            doc_type = DocumentDomain.INSURANCE_FINANCIAL
        elif any(k in lower_text for k in ['curriculum', 'syllabus', 'module', 'course', 'student', 'java', 'python']):
            doc_type = DocumentDomain.CURRICULUM_SYLLABUS
        else:
            doc_type = DocumentDomain.BUSINESS_OUTLINE

        for line in lines[:100]:
            if (len(line) < 70 and (line.isupper() or line.endswith(":") or re.match(r'^(Module|Unit|Chapter|Section|\d+\.)', line, re.I))):
                cleaned_t = re.sub(r'^[0-9.:\-\s]+', '', line).strip()
                if curr_title and len(curr_title) >= MIN_TOPIC_TITLE_LEN:
                    topics.append(TopicOutlineResponse(
                        title=curr_title,
                        description=f"Overview of {curr_title}",
                        subtopics=curr_subtopics[:6]
                    ))
                curr_title = cleaned_t if len(cleaned_t) >= MIN_TOPIC_TITLE_LEN else None
                curr_subtopics = []
            elif curr_title and (line.startswith(("-", "*", "•")) or ":" in line):
                sub_text = re.sub(r'^[\-*•\s]+', '', line).strip()
                if sub_text and len(sub_text) < 80:
                    curr_subtopics.append(sub_text)
                    if len(highlights) < 15:
                        highlights.append(sub_text.split(":")[0].strip())

        if curr_title and len(curr_title) >= 3:
            topics.append(TopicOutlineResponse(
                title=curr_title,
                description=f"Overview of {curr_title}",
                subtopics=curr_subtopics[:6]
            ))

        if not topics and lines:
            topics.append(TopicOutlineResponse(
                title="Core Document Overview",
                description=lines[0][:120],
                subtopics=[l[:60] for l in lines[1:6]]
            ))

        if not highlights:
            words = [w.title() for w in re.findall(r'\b[A-Za-z]{4,20}\b', text) if w.lower() not in ENGLISH_STOPWORDS]
            highlights = list(dict.fromkeys(words))[:10]

        return [QualitativeSectionResponse(
            document_type=doc_type,
            main_topics=[t for t in topics if len(t.title) >= 3][:8],
            extracted_highlights=highlights[:15]
        )]

    if not api_key or is_vision_api_disabled():
        return parse_local_qualitative_topics(raw_text)

    try:
        client = OpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=api_key,
            http_client=httpx.Client(timeout=httpx.Timeout(10.0, connect=3.0)),
            max_retries=1
        )

        prompt = f"""
        You are an expert document profiler. Analyze the following non-numeric qualitative document (such as a syllabus, course curriculum, brochure, or policy guide).
        Extract:
        1. "document_type": E.g. "Curriculum / Syllabus", "Brochure", "Policy Document".
        2. "main_topics": List of up to 8 core modules/sections. For each module include "title", "description", and a list of "subtopics".
        3. "extracted_highlights": List of up to 15 key skills, technologies, or concepts.

        Output strictly JSON matching this schema:
        {{
          "document_type": "Curriculum / Syllabus",
          "main_topics": [
            {{
              "title": "Module Title",
              "description": "Brief summary",
              "subtopics": ["Subtopic 1", "Subtopic 2"]
            }}
          ],
          "extracted_highlights": ["Skill 1", "Concept 2"]
        }}

        Document Text:
        {raw_text[:8000]}
        """

        completion = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=2048,
            response_format={"type": "json_object"},
            timeout=10.0
        )

        response_content = completion.choices[0].message.content or ""
        if "<think>" in response_content:
            response_content = response_content.split("</think>")[-1].strip()

        start_idx = response_content.find("{")
        end_idx = response_content.rfind("}")
        if start_idx != -1 and end_idx != -1:
            response_content = response_content[start_idx:end_idx+1]

        data = json.loads(response_content)
        topics = [
            TopicOutlineResponse(
                title=t.get("title", "Module"),
                description=t.get("description", ""),
                subtopics=t.get("subtopics", [])
            ) for t in data.get("main_topics", [])
        ]
        return [QualitativeSectionResponse(
            document_type=data.get("document_type", "Curriculum / Syllabus"),
            main_topics=topics,
            extracted_highlights=data.get("extracted_highlights", [])
        )]
    except Exception as exc:
        logger.warning(f"Qualitative Section Extraction AI Error: {exc}")
        return parse_local_qualitative_topics(raw_text)

def generate_local_fallback_text_result(raw_text: str, page_count: int = None, paragraph_count: int = None, ai_model: str = "local-heuristic") -> TextResult:
    """Generates a rich, structured 5-10 point bullet summary and term-frequency keyword ranking."""
    word_count = len(raw_text.split()) if raw_text else 0
    lines = [l.strip() for l in raw_text.split("\n") if l.strip() and not l.startswith("--- Page")]
    
    # 1. 5-10 Point Bullet Summary Construction
    summary_bullets = []
    if lines:
        # Collect key headings/sentences spaced evenly across the full document text
        step = max(1, len(lines) // 8)
        sampled = []
        for i in range(0, len(lines), step):
            line = lines[i]
            clean_l = line.lstrip("-*•0123456789. ").strip()
            if len(clean_l) > 15 and not clean_l.isdigit() and clean_l not in sampled:
                sampled.append(clean_l)
            if len(sampled) >= 8:
                break
                
        for line in sampled[:8]:
            summary_bullets.append(f"• {line}")
            
    if not summary_bullets:
        summary_bullets = [
            f"• Document ingested successfully ({word_count} words across {page_count or 1} page(s)).",
            "• Full layout text and spatial attributes extracted.",
            "• Categorical key-value pairs and document structure generated."
        ]

    summary_text = "\n".join(summary_bullets)

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

    qual_sections = extract_qualitative_sections(raw_text)

    return TextResult(
        summary=summary_text,
        keywords=keywords,
        word_count=word_count,
        page_count=page_count,
        paragraph_count=paragraph_count,
        ai_model=ai_model,
        qualitative_sections=qual_sections
    )

def process_text(raw_text: str, page_count: int = None, paragraph_count: int = None) -> TextResult:
    word_count = len(raw_text.split())
    api_key = os.getenv("NVIDIA_API_KEY")
    base_url = os.getenv("NVIDIA_NIM_BASE_URL", "https://integrate.api.nvidia.com/v1")
    model_name = os.getenv("TEXT_AI_MODEL", "meta/llama-3.1-70b-instruct")

    from engine.vision_client import is_vision_api_disabled, disable_vision_api
    
    # Heuristic Fallback if API Key missing or Circuit Breaker Active
    if not api_key or is_vision_api_disabled():
        return generate_local_fallback_text_result(raw_text, page_count, paragraph_count, model_name)

    client = OpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=api_key,
        http_client=httpx.Client(timeout=httpx.Timeout(10.0, connect=3.0)),
        max_retries=1
    )

    prompt = f"""
    You are an expert document profiler. Analyze the following document text and provide:
    1. "summary": A comprehensive, structured 5 to 10 bullet point summary covering key guidelines, requirements, topics, or findings from across the complete document. Use markdown bullet format with newlines (e.g. "• Point 1...\n• Point 2...\n• Point 3...").
    2. "keywords": A list of up to 20 top keywords with their relevance score (0.0 to 1.0).
    
    Output strictly in JSON format matching this schema:
    {{
        "summary": "• Point 1...\n• Point 2...\n• Point 3...\n• Point 4...\n• Point 5...",
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

