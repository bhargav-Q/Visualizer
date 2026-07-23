import os
import json
import base64
import time
import logging
from typing import Optional
from dotenv import load_dotenv
from openai import OpenAI
from engine.pydantic_models import DocumentAnalytics

logger = logging.getLogger(__name__)

load_dotenv()
api_key = os.getenv("NVIDIA_API_KEY")

VISION_MODEL_NAME = "meta/llama-3.2-11b-vision-instruct"

def get_openai_client() -> Optional[OpenAI]:
    """Returns an OpenAI client initialized with NVIDIA NIM base URL."""
    if not api_key:
        logger.warning("NVIDIA_API_KEY is missing from environment")
        return None
    return OpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=api_key
    )

def encode_image_to_base64(image_bytes: bytes) -> str:
    """Encodes raw image bytes into a Base64 data URL string."""
    encoded = base64.b64encode(image_bytes).decode("utf-8")
    return f"data:image/png;base64,{encoded}"

_api_disabled_until = 0.0

def is_vision_api_disabled() -> bool:
    global _api_disabled_until
    return time.time() < _api_disabled_until

def disable_vision_api(seconds: float = 60.0):
    global _api_disabled_until
    _api_disabled_until = time.time() + seconds
    logger.warning(f"NVIDIA API disabled globally for {seconds} seconds.")

def extract_analytics_with_vision(image_bytes: bytes, text_hint: str = "", max_retries: int = 3) -> Optional[DocumentAnalytics]:
    """
    Sends rendered PNG page image bytes to meta/llama-3.2-11b-vision-instruct
    to extract metrics, key-value pairs, tables, summary, and keywords.
    Enforces strict Pydantic JSON validation with retry backoff.
    """
    if is_vision_api_disabled():
        logger.warning("NVIDIA API is temporarily disabled due to rate limit/503 errors.")
        return None

    client = get_openai_client()
    if not client or not image_bytes:
        return None

    base64_url = encode_image_to_base64(image_bytes)

    prompt = f"""You are an expert document analysis and vision extraction system. Analyze the attached document image and extract ALL key information into a single structured JSON response.

Context Text Hint:
{text_hint[:2000]}

Return ONLY valid JSON matching this exact JSON schema:
{{
  "document_title": "<Title of the report or document>",
  "report_date": "<Date of report if available e.g. 2025-01-15 or null>",
  "summary": "<3-5 sentence TL;DR executive summary>",
  "keywords": ["<keyword 1>", "<keyword 2>", "<keyword 3>"],
  "metrics": [
    {{
      "category": "<Metric Category Name>",
      "metric_value": 12345.67,
      "unit": "<USD, %, kg, units or null>",
      "context_snippet": "<Exact sentence or row text supporting this metric>",
      "page_number": 1
    }}
  ],
  "key_value_pairs": [
    {{
      "key_name": "<Key / Label Name>",
      "value": "<Extracted Value>",
      "context_snippet": "<Supporting text phrase>",
      "page_number": 1
    }}
  ],
  "tables": [
    {{
      "table_title": "<Table Title>",
      "headers": ["<Col 1>", "<Col 2>", "<Col 3>"],
      "rows": [
        ["<Row 1 Cell 1>", "<Row 1 Cell 2>", "<Row 1 Cell 3>"]
      ],
      "page_number": 1
    }}
  ]
}}

CRITICAL EXTRACTION RULES:
- Numerical Metrics: Extract ALL numbers, revenues, expenses, counts, percentages, and metrics. Convert monetary values to pure floating-point numbers (e.g., "$45,000.50" -> 45000.5).
- Key-Value Pairs: Extract document attributes like Invoice #, Author, Organization, Account Number, Status, Tax ID.
- Tables: Extract header columns and cell rows preserving left-to-right cell order.
- Context Snippets: Include the exact sentence supporting each metric so cell coordinates can be matched.
"""

    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": base64_url}}
            ]
        }
    ]

    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Querying NIM Vision API model '{VISION_MODEL_NAME}' (Attempt {attempt}/{max_retries})...")
            completion = client.chat.completions.create(
                model=VISION_MODEL_NAME,
                messages=messages,
                temperature=0.2,
                max_tokens=4096,
                timeout=45.0
            )

            content = completion.choices[0].message.content.strip()

            # Clean reasoning tags if model includes them
            if "<think>" in content:
                content = content.split("</think>")[-1].strip() if "</think>" in content else content.split("<think>")[-1].strip()

            start_idx = content.find("{")
            end_idx = content.rfind("}")
            if start_idx != -1 and end_idx != -1:
                content = content[start_idx:end_idx+1]

            data = json.loads(content)
            try:
                analytics = DocumentAnalytics(**data)
            except Exception as val_err:
                logger.warning(f"Vision LLM Pydantic validation warning on attempt {attempt}: {val_err}. Sanitizing data fields...")
                # Sanitize dict entries if Pydantic model validation needs relaxation
                if isinstance(data, dict):
                    metrics_list = data.get("metrics") or []
                    sanitized_metrics = []
                    for m in metrics_list:
                        if isinstance(m, dict):
                            val = m.get("metric_value")
                            try:
                                float_val = float(str(val).replace("$", "").replace(",", "")) if val is not None else 0.0
                            except ValueError:
                                float_val = 0.0
                            m["metric_value"] = float_val
                            sanitized_metrics.append(m)
                    data["metrics"] = sanitized_metrics

                    tbls_list = data.get("tables") or []
                    sanitized_tbls = []
                    for t in tbls_list:
                        if isinstance(t, dict) and isinstance(t.get("rows"), list):
                            clean_rows = []
                            for row in t["rows"]:
                                if isinstance(row, list):
                                    clean_row = [str(cell) if cell is not None else "" for cell in row]
                                    clean_rows.append(clean_row)
                            t["rows"] = clean_rows
                            sanitized_tbls.append(t)
                    data["tables"] = sanitized_tbls

                    analytics = DocumentAnalytics(**data)
                else:
                    raise val_err

            logger.info(f"Successfully validated DocumentAnalytics vision response: {len(analytics.metrics)} metrics, {len(analytics.key_value_pairs)} KV pairs, {len(analytics.tables)} tables")
            return analytics

        except json.JSONDecodeError as json_err:
            logger.warning(f"Vision LLM JSON parse error on attempt {attempt}: {json_err}")
            if attempt < max_retries:
                time.sleep(2)
        except Exception as err:
            logger.warning(f"Vision LLM API error on attempt {attempt}: {err}")
            status_code = getattr(err, "status_code", None)
            is_rate_limit = False
            is_timeout = False
            
            if status_code in (429, 503) or "503" in str(err) or "429" in str(err) or "ResourceExhausted" in str(err):
                is_rate_limit = True
            
            # Check for request timeouts
            if "timeout" in str(err).lower() or "timed out" in str(err).lower() or "timeout" in type(err).__name__.lower():
                is_timeout = True

            if is_timeout:
                logger.warning("NVIDIA API request timed out. Disabling API calls globally for 120 seconds to prevent hangs.")
                disable_vision_api(120.0)
                break  # Fail fast immediately on timeouts

            if is_rate_limit:
                if attempt < max_retries:
                    logger.info(f"Rate limit or service unavailable detected (status {status_code}). Sleeping 2 seconds before retry...")
                    time.sleep(2)
                else:
                    logger.warning("NVIDIA API repeatedly failed with rate limits. Disabling API calls globally for 60 seconds.")
                    disable_vision_api(60.0)
            elif attempt < max_retries:
                time.sleep(2 ** attempt) # Exponential backoff for other transient errors

    return None
