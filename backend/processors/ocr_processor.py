import os
import json
import logging
from dotenv import load_dotenv

from pathlib import Path

logger = logging.getLogger(__name__)

# Load environment variables (.env in project root or current dir)
env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)
load_dotenv()
api_key = os.getenv("NVIDIA_API_KEY")

def parse_tsv_grid(raw_text: str) -> dict | None:
    """
    Patch C: Deterministic TSV Table Parser.
    Parses tab-separated text lines directly into a structured table object
    without relying on LLM availability.
    """
    lines = [line.strip() for line in raw_text.split("\n") if "\t" in line]
    if len(lines) < 2:
        return None

    parsed_rows = []
    for line in lines:
        cells = [c.strip() for c in line.split("\t")]
        # Convert numeric and currency strings to numbers where possible
        clean_cells = []
        for cell in cells:
            if not cell or cell in ["--", "-", "null"]:
                clean_cells.append(None)
            else:
                # Strip currency symbols and commas
                clean_val = cell.replace("$", "").replace(",", "").strip()
                try:
                    if "." in clean_val:
                        clean_cells.append(float(clean_val))
                    else:
                        clean_cells.append(int(clean_val))
                except ValueError:
                    clean_cells.append(cell)
        parsed_rows.append(clean_cells)

    if len(parsed_rows) >= 2 and len(parsed_rows[0]) >= 2:
        headers = [str(h) if h is not None else f"Column_{idx+1}" for idx, h in enumerate(parsed_rows[0])]
        data_rows = parsed_rows[1:]
        return {
            "headers": headers,
            "rows": data_rows
        }
    return None

def extract_tables_from_text(raw_text: str) -> dict | None:
    """
    Hybrid DeepSeek AI + Deterministic TSV Table Extractor.
    Takes document/image text, performs deterministic TSV grid parsing,
    and queries DeepSeek AI for table cleaning and normalization.
    """
    if not raw_text or not raw_text.strip():
        logger.info("No text content provided for table extraction.")
        return None

    # Step 1: Check deterministic TSV backstop (Patch C)
    deterministic_table = parse_tsv_grid(raw_text)

    from openai import OpenAI

    from engine.vision_client import is_vision_api_disabled, disable_vision_api

    if not api_key or is_vision_api_disabled():
        logger.warning("NVIDIA_API_KEY missing or API disabled — using deterministic TSV table fallback if available")
        return deterministic_table

    try:
        client = OpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=api_key
        )

        prompt = f"""You are an expert tabular data extraction system. Analyze the following document or image text and extract ALL structured tables, data grids, invoices, claims lists, or financial reports into a single combined JSON table.

Return ONLY valid JSON matching this exact JSON schema structure:
{{
  "has_table": true,
  "headers": ["<Column 1 Name>", "<Column 2 Name>", "<Column 3 Name>", "... (Include ALL N Column Headers from document)"],
  "rows": [
    ["<Row 1 Cell 1>", "<Row 1 Cell 2>", "<Row 1 Cell 3>", "... (Include ALL N Cells matching headers)"],
    ["<Row 2 Cell 1>", "<Row 2 Cell 2>", "<Row 2 Cell 3>", "... (Include ALL N Cells matching headers)"]
  ]
}}


CRITICAL RULES:
- DYNAMIC HEADERS: Extract ALL original column headers dynamically as they appear in the source document. Do NOT restrict or merge columns into a fixed 4-column schema. If the table has 8, 12, or 18 columns, extract ALL 8, 12, or 18 columns!
- Preserve exact column order from left to right. 
- Replace dashes ("--"), blank cells, or missing values with null or "".
- Convert monetary amounts and numeric values to pure numbers (e.g. "$1,600" -> 1600, "28,340.47" -> 28340.47).
- Keep descriptions, order IDs, product names, dates, and text codes as clean strings.
- If 2 or more rows of structured or tabular data are found anywhere in the document, set "has_table": true.
- ONLY return "has_table": false if the entire document is purely unstructured narrative text with zero lists/tables.

Document Text:
{raw_text[:60000]}"""


        model_name = os.getenv("TABLE_AI_MODEL", "deepseek-ai/deepseek-v4-flash")
        logger.info(f"Sending document text to AI model {model_name} for table extraction...")

        
        kwargs = {
            "model": model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
            "max_tokens": 4096,
            "response_format": {"type": "json_object"},
            "timeout": 45.0
        }
        if "deepseek" in model_name.lower():
            kwargs["extra_body"] = {"chat_template_kwargs": {"thinking": False}}

        completion = client.chat.completions.create(**kwargs)


        content = completion.choices[0].message.content.strip()
        
        # Strip DeepSeek AI <think>...</think> reasoning blocks if present
        if "<think>" in content:
            if "</think>" in content:
                content = content.split("</think>")[-1].strip()
            else:
                content = content.split("<think>")[-1].strip()

        # Extract pure JSON string between first '{' and last '}'
        start_idx = content.find("{")
        end_idx = content.rfind("}")
        if start_idx != -1 and end_idx != -1:
            content = content[start_idx:end_idx+1]

        data = json.loads(content)
        if data.get("has_table") and data.get("headers") and data.get("rows"):
            logger.info(f"DeepSeek AI extracted table: {len(data['headers'])} headers, {len(data['rows'])} rows")
            return {
                "headers": data["headers"],
                "rows": data["rows"]
            }

    except Exception as e:
        logger.warning(f"DeepSeek AI table extraction error: {e}")
        status_code = getattr(e, "status_code", None)
        err_msg = str(e).lower()
        if status_code in (429, 503) or "503" in err_msg or "429" in err_msg or "resourceexhausted" in err_msg:
            logger.warning("Table Processor hit rate limit or 503 error. Disabling API calls globally for 60 seconds.")
            disable_vision_api(60.0)
        elif "timeout" in err_msg or "timed out" in err_msg or "timeout" in type(e).__name__.lower():
            logger.warning("Table Processor request timed out. Disabling API calls globally for 120 seconds.")
            disable_vision_api(120.0)

    # Step 2: Fallback to deterministic TSV backstop if DeepSeek fails or returns no table
    if deterministic_table:
        logger.info(f"Using deterministic TSV table backstop: {len(deterministic_table['headers'])} headers, {len(deterministic_table['rows'])} rows")
        return deterministic_table

    return None

def extract_tables_from_pdf(file_bytes: bytes) -> dict | None:
    """
    Reads document text via PyMuPDF and calls extract_tables_from_text.
    """
    import pymupdf
    try:
        doc = pymupdf.open(stream=file_bytes, filetype="pdf")
        full_text = ""
        for page in doc:
            full_text += page.get_text() + "\n"
        return extract_tables_from_text(full_text)
    except Exception as e:
        logger.warning(f"Error extracting PDF text for table extraction: {e}")
        return None

def extract_tables_with_nemotron_ocr(image_bytes: bytes) -> dict | None:
    """
    Invokes NVIDIA Nemotron OCR v2 endpoint (https://ai.api.nvidia.com/v1/cv/nvidia/nemotron-ocr-v2)
    with base64 encoded image payload as per NVIDIA specifications.
    """
    if not api_key or not image_bytes:
        return None

    import base64
    import requests

    invoke_url = os.getenv("NEMOTRON_OCR_URL", "https://ai.api.nvidia.com/v1/cv/nvidia/nemotron-ocr-v2")
    image_b64 = base64.b64encode(image_bytes).decode()

    if len(image_b64) > 180000:
        logger.warning("Image payload exceeds 180,000 base64 characters limit for Nemotron OCR v2 direct payload — rejecting to avoid silent API failure")
        return None

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json"
    }

    payload = {
        "input": [
            {
                "type": "image_url",
                "url": f"data:image/png;base64,{image_b64}"
            }
        ]
    }

    try:
        response = requests.post(invoke_url, headers=headers, json=payload, timeout=30.0)
        if response.status_code == 200:
            res = response.json()
            logger.info("Successfully received Nemotron OCR v2 API response")
            return res
        else:
            logger.warning(f"Nemotron OCR v2 returned status {response.status_code}: {response.text}")
    except Exception as e:
        logger.warning(f"Nemotron OCR v2 API error: {e}")

    return None


def extract_page_with_nemotron_sectioned(page, dpi=150, max_b64_chars=170000):
    """
    Problem 2 Fix: Auto page-section splitting for Nemotron OCR v2.
    Renders a PyMuPDF page in vertical sections that each fit under the
    180K base64 character limit, sends each section to Nemotron OCR v2,
    and merges all text_detections into one combined result.
    If the Nemotron Cloud API returns an error or is unavailable, falls back gracefully.

    Args:
        page: A PyMuPDF page object.
        dpi: Render resolution (default 150 for crisp text).
        max_b64_chars: Maximum base64 characters per section (default 170K with 10K safety margin).

    Returns:
        List of raw text strings extracted from all sections, or fallback results on failure.
    """
    import base64
    import pymupdf

    rect = page.rect
    page_height = rect.y1 - rect.y0

    # Start with full page to check if it fits
    pix_full = page.get_pixmap(dpi=dpi)
    full_b64_len = len(base64.b64encode(pix_full.tobytes("png")))

    result = None
    has_failed = False

    if full_b64_len <= max_b64_chars:
        # Full page fits — send as one request
        try:
            result = extract_tables_with_nemotron_ocr(pix_full.tobytes("png"))
            if not result or not result.get("data"):
                has_failed = True
        except Exception as err:
            logger.warning(f"Nemotron OCR direct request error: {err}")
            has_failed = True
    else:
        # Calculate how many vertical sections we need
        ratio = full_b64_len / max_b64_chars
        num_sections = max(2, int(ratio) + 1)
        section_height = page_height / num_sections

        logger.info(f"Page too large ({full_b64_len:,} b64 chars). Splitting into {num_sections} vertical sections.")

        all_texts = []
        for i in range(num_sections):
            y_start = rect.y0 + (i * section_height)
            y_end = rect.y0 + ((i + 1) * section_height)
            clip = pymupdf.Rect(rect.x0, y_start, rect.x1, y_end)

            pix_section = page.get_pixmap(dpi=dpi, clip=clip)
            section_bytes = pix_section.tobytes("png")

            try:
                sec_res = extract_tables_with_nemotron_ocr(section_bytes)
                if sec_res and sec_res.get("data"):
                    detections = sec_res["data"][0].get("text_detections", [])
                    section_texts = [d["text_prediction"]["text"] for d in detections]
                    all_texts.extend(section_texts)
                else:
                    has_failed = True
                    break
            except Exception as err:
                logger.warning(f"Nemotron OCR section request error at section {i+1}: {err}")
                has_failed = True
                break
        
        if not has_failed:
            return all_texts

    # ⚠️ Automatic Fallback Logic: Triggered if Cloud Nemotron API is down, rate-limited, or unauthorized (404/403/503)
    if has_failed or not result:
        logger.warning("[WARNING] Cloud Nemotron OCR API unavailable. Falling back to local RapidOCR / Vision LLM.")
        
        # Fallback Option A: Local RapidOCR
        try:
            from parsers.pdf_parser import get_ocr_engine
            ocr_engine = get_ocr_engine()
            if ocr_engine:
                from parsers.spatial_grid import run_ocr_with_orientation_check
                logger.info("Executing Fallback A: local RapidOCR engine...")
                ocr_results = run_ocr_with_orientation_check(page, ocr_engine, dpi=dpi)
                if ocr_results:
                    return [str(item[1]).strip() for item in ocr_results if item[1]]
        except Exception as ocr_err:
            logger.warning(f"Local RapidOCR fallback failed: {ocr_err}")

        # Fallback Option B: Llama-3.2-Vision (NVIDIA API)
        try:
            from engine.vision_client import extract_analytics_with_vision
            logger.info("Executing Fallback B: meta/llama-3.2-11b-vision-instruct...")
            pix = page.get_pixmap(dpi=dpi)
            analytics = extract_analytics_with_vision(pix.tobytes("png"))
            if analytics:
                texts = []
                if analytics.summary:
                    texts.append(analytics.summary)
                for m in analytics.metrics:
                    if m.context_snippet:
                        texts.append(m.context_snippet)
                for kv in analytics.key_value_pairs:
                    if kv.context_snippet:
                        texts.append(kv.context_snippet)
                return texts
        except Exception as vision_err:
            logger.warning(f"Vision LLM fallback failed: {vision_err}")

        return []

    # Successful direct Nemotron OCR result parsing
    detections = result["data"][0].get("text_detections", [])
    return [d["text_prediction"]["text"] for d in detections]
