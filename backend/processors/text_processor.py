import os
import json
from openai import OpenAI
from models.schemas import TextResult, KeywordItem

# Get API key from environment
api_key = os.getenv("NVIDIA_API_KEY")

def process_text(raw_text: str, page_count: int = None, paragraph_count: int = None) -> TextResult:
    word_count = len(raw_text.split())
    
    # Base fallback in case API fails
    model_name = "deepseek-ai/deepseek-v4-flash"
    fallback_summary = "Summary unavailable — AI service is temporarily down."
    fallback_keywords = []

    if not api_key:
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
            temperature=1,
            top_p=0.95,
            max_tokens=16384,
            extra_body={"chat_template_kwargs": {"thinking": True, "reasoning_effort": "high"}},
            stream=False,
            response_format={"type": "json_object"}
        )
        
        # Optional: Print reasoning if it exists (for debugging)
        reasoning = getattr(completion.choices[0].message, "reasoning", None) or getattr(completion.choices[0].message, "reasoning_content", None)
        if reasoning:
            print("AI Reasoning:", reasoning)

        response_content = completion.choices[0].message.content
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
        return TextResult(
            summary=fallback_summary,
            keywords=fallback_keywords,
            word_count=word_count,
            page_count=page_count,
            paragraph_count=paragraph_count,
            ai_model=model_name
        )
