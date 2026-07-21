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

    if not api_key:
        logger.warning("NVIDIA_API_KEY missing — using deterministic TSV table fallback if available")
        return deterministic_table

    try:
        client = OpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=api_key
        )

        prompt = f"""You are an expert tabular data extraction system. Analyze the following document or image text and extract ALL structured tables, claims lists, loss-run reports, rating worksheets, payroll breakdowns, or invoice schedules across ALL pages into a single combined JSON table.

Return ONLY valid JSON matching this exact structure:
{{
  "has_table": true,
  "headers": ["CLASS CODE / ITEM", "DESCRIPTION / YEAR", "COUNT / EMPLOYEES", "AMOUNT / PAYROLL"],
  "rows": [
    ["172", "Truck Farm", 85, 2700000],
    ["8810", "Clerical Office Employees - NOC", 2, 175000],
    ["4007611", "2025 Open Claim", 1, 1600],
    ["0286657", "2021 Closed Claim", 1, 136300]
  ]
}}

Rules:
- Actively extract and combine ALL grid tables, Loss-Run reports, Parsed Claims, rating worksheets, or financial breakdowns from ALL pages.
- Replace dashes ("--"), blank cells, or missing values with null or "".
- Identify unified, clean column headers (e.g. "ITEM / CODE", "DESCRIPTION", "COUNT / EMPLOYEES", "AMOUNT / PAYROLL").
- Convert monetary amounts and numeric values to pure numbers (e.g. "$1,600" -> 1600, "$2,700,000" -> 2700000).
- Keep descriptions, statuses, claim numbers, and dates as clean strings.
- If 2 or more rows of structured or tabular data are found anywhere in the document, set "has_table": true.
- ONLY return "has_table": false if the entire document is purely unstructured narrative text with zero lists/tables.

Document Text:
{raw_text[:60000]}"""

        logger.info("Sending document text to DeepSeek AI for table extraction...")
        completion = client.chat.completions.create(
            model="deepseek-ai/deepseek-v4-flash",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=4096,
            extra_body={"chat_template_kwargs": {"thinking": False}},
            response_format={"type": "json_object"},
            timeout=30.0
        )

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

