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

def extract_tables_from_pdf(file_bytes: bytes) -> dict | None:
    """
    Pure Prompt-Based DeepSeek AI Table Extractor.
    Reads document text via PyMuPDF and uses deepseek-ai/deepseek-v4-flash
    to extract, resolve headers, clean numbers, and return structured table JSON.
    """
    import pymupdf
    from openai import OpenAI

    if not api_key:
        logger.warning("NVIDIA_API_KEY missing — cannot run DeepSeek AI table extraction")
        return None

    try:
        # Extract text from PDF in-memory
        doc = pymupdf.open(stream=file_bytes, filetype="pdf")
        full_text = ""
        for page in doc:
            full_text += page.get_text() + "\n"
        
        if not full_text.strip():
            logger.info("No text content found in PDF.")
            return None

        client = OpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=api_key
        )

        prompt = f"""You are an expert tabular data extraction system. Analyze the following full multi-page document text and extract ALL structured tables, claims lists, loss-run reports, rating worksheets, payroll breakdowns, or invoice schedules across ALL pages into a single combined JSON table.

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

Document Text (All Pages):
{full_text[:25000]}"""

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
                # If thinking wasn't closed properly
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

    return None
