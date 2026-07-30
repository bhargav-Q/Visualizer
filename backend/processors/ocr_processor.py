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
    Patch C: Deterministic Multi-Column Table Parser.
    Parses tab-separated, pipe-separated, or multi-space separated text lines
    directly into a structured table object without relying on LLM availability.
    """
    if not raw_text:
        return None

    import re
    lines = [line.strip() for line in raw_text.split("\n") if line.strip()]
    candidate_rows = []

    for line in lines:
        if "\t" in line:
            cells = [c.strip() for c in line.split("\t") if c.strip() != ""]
        elif "|" in line:
            cells = [c.strip() for c in line.split("|") if c.strip() != ""]
        else:
            cells = [c.strip() for c in re.split(r"\s{2,}", line) if c.strip() != ""]

        if len(cells) >= 2:
            clean_cells = []
            for cell in cells:
                if not cell or cell in ["--", "-", "null"]:
                    clean_cells.append(None)
                else:
                    clean_val = cell.replace("$", "").replace(",", "").strip()
                    try:
                        if "." in clean_val:
                            clean_cells.append(float(clean_val))
                        else:
                            clean_cells.append(int(clean_val))
                    except ValueError:
                        clean_cells.append(cell)
            candidate_rows.append(clean_cells)

    logger.info(f"[OCR_DEBUG] parse_tsv_grid len(candidate_rows) before filtering: {len(candidate_rows)}")
    if len(candidate_rows) >= 2:
        col_counts = [len(r) for r in candidate_rows]
        dominant_cols = max(set(col_counts), key=col_counts.count)
        logger.info(f"[OCR_DEBUG] parse_tsv_grid full col_counts: {col_counts}")
        logger.info(f"[OCR_DEBUG] parse_tsv_grid computed dominant_cols: {dominant_cols}")
        if dominant_cols >= 2:
            matching_rows = [r for r in candidate_rows if len(r) == dominant_cols]
            dropped_rows = [r for r in candidate_rows if len(r) != dominant_cols]
            logger.info(f"[OCR_DEBUG] parse_tsv_grid len(matching_rows) after filtering: {len(matching_rows)}")
            for idx, dropped in enumerate(dropped_rows):
                logger.info(f"[OCR_DEBUG] parse_tsv_grid dropped row {idx} (len={len(dropped)} != dominant_cols={dominant_cols}): {dropped}")

            if len(matching_rows) >= 2:
                # Check if column 0 is predominantly question/bullet index markers (e.g. (a), (b), (c), 1., 2.)
                col0_vals = [str(r[0]).strip().lower() for r in matching_rows if r]
                question_markers = sum(1 for v in col0_vals if re.match(r"^[\(\[\{]?[a-z0-9]{1,3}[\)\.\}\]]?$", v))
                if question_markers / len(col0_vals) > 0.35:
                    return None

                headers = [str(h) if h is not None else f"Column_{idx+1}" for idx, h in enumerate(matching_rows[0])]
                data_rows = matching_rows[1:]
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

    # NVIDIA API temporarily bypassed for pure Mistral OCR testing phase
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


        model_name = os.getenv("TABLE_AI_MODEL", "meta/llama-3.1-70b-instruct")
        logger.info(f"Sending document text to AI model {model_name} for table extraction...")

        
        kwargs = {
            "model": model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
            "max_tokens": 4096,
            "response_format": {"type": "json_object"},
            "timeout": 15.0
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

async def extract_tables_from_text_async(raw_text: str) -> dict | None:
    """Async wrapper for extract_tables_from_text enforcing 15-second non-blocking execution."""
    import asyncio
    try:
        return await asyncio.to_thread(extract_tables_from_text, raw_text)
    except Exception as exc:
        logger.warning(f"Async table extraction call failed: {exc}")
        return None
