import json
import os
import re
import logging
from collections import Counter
from openai import OpenAI

from pydantic import BaseModel, Field, ValidationError, ConfigDict
from typing import List, Optional, Any, Union

logger = logging.getLogger(__name__)

# WHY: We cap input markdown context at 25,000 characters before calling DeepSeek.
# Large multi-page PDF documents (30+ pages) generate markdown exceeding 50k+ chars, which can 
# exceed LLM token window limits or cause API timeouts. 25k chars captures key titles, rating 
# sheets, and loss runs from initial document pages.
MAX_INPUT_CONTEXT_LEN = 25000

class KPIValidationSchema(BaseModel):
    model_config = ConfigDict(strict=True)
    label: str
    value: str
    page_range: Optional[str] = None

class KeyValueValidationSchema(BaseModel):
    model_config = ConfigDict(strict=False)
    key_name: str
    value: Any
    page_number: Optional[int] = 1
    context_snippet: Optional[str] = None

class KeywordValidationSchema(BaseModel):
    model_config = ConfigDict(strict=True)
    word: str
    score: Union[int, float]

class ChartValidationSchema(BaseModel):
    model_config = ConfigDict(strict=True)
    title: str
    chart_type: str
    x_axis_label: Optional[str] = "Category"
    y_axis_label: Optional[str] = "Value"
    x_data: List[Union[str, int, float]]
    y_data: List[Union[int, float]]
    page_range: Optional[str] = None

class DashboardSpecValidationSchema(BaseModel):
    model_config = ConfigDict(strict=True)
    dashboard_title: str
    executive_summary: str
    kpis: List[KPIValidationSchema] = Field(default_factory=list)
    key_value_pairs: List[KeyValueValidationSchema] = Field(default_factory=list)
    keywords: List[KeywordValidationSchema] = Field(default_factory=list)
    charts: List[ChartValidationSchema] = Field(default_factory=list)

def generate_dashboard_spec_from_markdown(markdown_text: str) -> dict:
    """
    Uses NVIDIA NIM's DeepSeek-V4-Flash model to convert extracted document Markdown
    into a standardized, structured Dashboard JSON specification for the frontend.
    """
    nvidia_api_key = os.environ.get("NVIDIA_API_KEY")
    if not nvidia_api_key:
        logger.warning("NVIDIA_API_KEY is missing from environment variables. Returning fallback dashboard spec.")
        return generate_heuristic_fallback_dashboard_spec(markdown_text)

    # Initialize OpenAI client pointing to NVIDIA NIM API
    client = OpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=nvidia_api_key
    )

    system_prompt = """
    You are an expert Data Visualization Architect.
    Analyze the provided document markdown (including its embedded tables, equations, key facts, and ## Page X headings) 
    and synthesize a structured dashboard specification.

    Output STRICTLY a valid JSON object matching this schema:
    {
      "dashboard_title": "Descriptive Document Title",
      "executive_summary": "2-3 sentence overview of core findings and key highlights",
      "kpis": [
        {
          "label": "Metric Name",
          "value": "Formatted Value (e.g. $4.2M, 904 Words, 12 Pages, 15%)",
          "page_range": "Page 1 or Pages 1, 23"
        }
      ],
      "key_value_pairs": [
        {
          "key_name": "Attribute Name (e.g. Effective Date, Applicant Name, FEIN Number)",
          "value": "Attribute Value (e.g. 10/04/2025, Surf Packing Inc., 81-2831387)",
          "page_number": 1,
          "context_snippet": "Context snippet from text"
        }
      ],
      "keywords": [
        {"word": "PrimaryKeyword", "score": 0.95},
        {"word": "SecondaryKeyword", "score": 0.85}
      ],
      "charts": [
        {
          "title": "Chart Title",
          "chart_type": "bar | line | pie",
          "x_axis_label": "Category Label",
          "y_axis_label": "Value Label",
          "x_data": ["Category 1", "Category 2"],
          "y_data": [100, 200],
          "page_range": "Page 1 or Pages 1-3"
        }
      ]
    }
    Rules:
    - Extract real quantitative values from tables and text.
    - Extract 10 to 25 key domain attributes/facts into key_value_pairs (e.g. Effective Date, FEIN, Address, Producer, Carrier, Industry, Safety Programs, Wages).
    - For each KPI and Chart, identify the exact source page number or page range (e.g. "Page 1", "Pages 1, 23", "Page 22") based on the document headings like "## Page X" or document section structure.
    - Extract 10-15 dominant domain keywords with relevance scores from 0.40 to 0.98.
    - If numbers exist in tables, construct at least 1-2 visual charts (bar, line, or pie).
    - Ensure x_data and y_data arrays match in length and contain numbers in y_data.
    - Output ONLY raw valid JSON. Do not write markdown codeblock wrappers like ```json.
    """

    input_context = markdown_text[:MAX_INPUT_CONTEXT_LEN] if len(markdown_text) > MAX_INPUT_CONTEXT_LEN else markdown_text

    try:
        response = client.chat.completions.create(
            model="deepseek-ai/deepseek-v4-flash",
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": f"Document Markdown:\n\n{input_context}",
                },
            ],
            temperature=0.2,
            response_format={"type": "json_object"},
        )

        raw_content = response.choices[0].message.content or ""
        # Clean any backtick JSON blocks if returned
        clean_json_str = re.sub(r"^```json\s*", "", raw_content.strip(), flags=re.IGNORECASE)
        clean_json_str = re.sub(r"\s*```$", "", clean_json_str.strip())
        
        parsed_spec = json.loads(clean_json_str)

        # WHY: DeepSeek LLM output can occasionally return incomplete keys (e.g. missing 'keywords' or 'charts') 
        # or fail entirely under rate limits / network dropouts. Instead of returning an incomplete spec or crashing, 
        # we check each expected key and fall back to local heuristic extraction functions (regex table parsing, 
        # term-frequency keyword ranking) to guarantee 100% UI dashboard uptime.
        if not parsed_spec.get("keywords"):
            parsed_spec["keywords"] = extract_local_keywords(markdown_text)
        if not parsed_spec.get("charts"):
            parsed_spec["charts"] = extract_charts_from_markdown_tables(markdown_text)
        if not parsed_spec.get("key_value_pairs"):
            parsed_spec["key_value_pairs"] = extract_local_key_value_pairs(markdown_text)

        # WHY: DeepSeek LLM output can return malformed shapes or non-numeric y_data (e.g. ["100", "N/A"]).
        # We validate parsed_spec against strict Pydantic schemas (DashboardSpecValidationSchema). 
        # If validation fails, we route to generate_heuristic_fallback_dashboard_spec to ensure 100% UI stability.
        try:
            validated_obj = DashboardSpecValidationSchema(**parsed_spec)
            return validated_obj.model_dump()
        except ValidationError as val_err:
            logger.warning(f"DeepSeek returned invalid spec schema structure: {val_err}. Routing to heuristic fallback.")
            return generate_heuristic_fallback_dashboard_spec(markdown_text)

    except Exception as exc:
        logger.error(f"Error calling NVIDIA DeepSeek-V4-Flash model: {exc}")
        return generate_heuristic_fallback_dashboard_spec(markdown_text)

def extract_local_key_value_pairs(markdown_text: str, max_pairs: int = 20) -> list:
    """
    Parses key-value pairs (Key: Value or | Key | Value |) from Markdown text with page numbers.
    """
    kv_list = []
    lines = markdown_text.split("\n")
    current_page = 1

    for line in lines:
        page_match = re.search(r"##\s*Page\s*(\d+)", line, re.IGNORECASE)
        if page_match:
            try:
                current_page = int(page_match.group(1))
            except ValueError:
                pass
            continue

        clean_line = line.strip()
        if not clean_line or clean_line.startswith("#") or clean_line.startswith("```"):
            continue

        # Check for Key: Value format
        if ":" in clean_line and not clean_line.startswith("|") and not clean_line.startswith(">"):
            parts = clean_line.split(":", 1)
            k_name = re.sub(r"[^\w\s-]", "", parts[0]).strip()
            v_val = parts[1].strip()
            if k_name and v_val and 3 <= len(k_name) <= 40 and 1 <= len(v_val) <= 120:
                if not any(stop in k_name.lower() for stop in ["http", "https", "image", "page", "header", "footer", "table"]):
                    kv_list.append({
                        "key_name": k_name,
                        "value": v_val,
                        "context_snippet": clean_line[:150],
                        "page_number": current_page
                    })

        # Check for 2-column Markdown tables (| Key | Value |)
        elif clean_line.startswith("|") and clean_line.count("|") == 3:
            cells = [c.strip() for c in clean_line.strip("|").split("|")]
            if len(cells) == 2 and cells[0] and cells[1] and not cells[0].startswith("-"):
                k_name = re.sub(r"[^\w\s-]", "", cells[0]).strip()
                v_val = cells[1].strip()
                if k_name and v_val and 3 <= len(k_name) <= 40 and 1 <= len(v_val) <= 120:
                    if k_name.lower() not in ["key", "attribute", "field", "name", "parameter"]:
                        kv_list.append({
                            "key_name": k_name,
                            "value": v_val,
                            "context_snippet": f"{k_name}: {v_val}",
                            "page_number": current_page
                        })

        if len(kv_list) >= max_pairs:
            break

    return kv_list[:max_pairs]

def extract_charts_from_markdown_tables(markdown_text: str) -> list:
    """
    Parses Markdown grid tables (| Col 1 | Col 2 |) and converts numerical columns into visual chart objects with page tracking.
    """
    charts = []
    lines = markdown_text.split("\n")
    table_blocks = []
    current_table = []
    current_page = "1"

    for line in lines:
        page_match = re.search(r"##\s*Page\s*(\d+)", line, re.IGNORECASE)
        if page_match:
            current_page = page_match.group(1)

        if "|" in line and not line.strip().startswith(">"):
            current_table.append((line.strip(), f"Page {current_page}"))
        else:
            if len(current_table) >= 3:
                table_blocks.append(current_table)
            current_table = []

    if len(current_table) >= 3:
        table_blocks.append(current_table)

    for idx, block in enumerate(table_blocks):
        try:
            raw_lines = [item[0] for item in block]
            page_tags = list(dict.fromkeys([item[1] for item in block]))
            page_range_str = ", ".join(page_tags) if page_tags else "Page 1"

            headers = [c.strip() for c in raw_lines[0].strip("|").split("|")]
            if len(headers) < 2:
                continue

            data_rows = []
            for row_line in raw_lines[2:]:
                if ":" in row_line and "-" in row_line:
                    continue  # Separator line
                cells = [c.strip() for c in row_line.strip("|").split("|")]
                if len(cells) == len(headers):
                    data_rows.append(cells)

            if not data_rows:
                continue

            x_col_idx = 0
            y_col_idx = None
            y_data = []

            for c_idx in range(1, len(headers)):
                numeric_vals = []
                for r in data_rows:
                    val_str = re.sub(r"[^\d.-]", "", r[c_idx])
                    if val_str:
                        try:
                            numeric_vals.append(float(val_str))
                        except ValueError:
                            pass
                if len(numeric_vals) == len(data_rows) and len(numeric_vals) > 0:
                    y_col_idx = c_idx
                    y_data = numeric_vals
                    break

            if y_col_idx is not None and len(y_data) > 0:
                x_data = [r[x_col_idx] for r in data_rows]
                charts.append({
                    "title": f"Extracted Chart: {headers[y_col_idx]} by {headers[x_col_idx]}",
                    "chart_type": "bar",
                    "x_axis_label": headers[x_col_idx],
                    "y_axis_label": headers[y_col_idx],
                    "x_data": x_data,
                    "y_data": y_data,
                    "page_range": page_range_str
                })
        except Exception as e:
            logger.debug(f"Could not parse table block {idx} into chart: {e}")

    return charts

def extract_local_keywords(text: str, top_n: int = 14) -> list:
    """Extracts dominant keywords by frequency with normalized relevance scores."""
    words = [re.sub(r"[^\w]", "", w).capitalize() for w in text.split() if len(re.sub(r"[^\w]", "", w)) > 3]
    stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by", "from", "is", "are", "was", "were", "be", "been", "have", "has", "had", "will", "would", "this", "that", "these", "those", "page", "header", "footer", "total", "index", "section"}
    filtered = [w for w in words if w.lower() not in stop_words and not w.isdigit()]
    counts = Counter(filtered).most_common(top_n)
    
    if not counts:
        return [{"word": "Overview", "score": 0.95}, {"word": "Analysis", "score": 0.85}]
        
    max_c = counts[0][1]
    return [{"word": w, "score": round(0.45 + (c / max_c) * 0.50, 2)} for w, c in counts]

def generate_heuristic_fallback_dashboard_spec(markdown_text: str) -> dict:
    """Local heuristic fallback when LLM API call fails or key is unconfigured."""
    lines = [l.strip() for l in markdown_text.split("\n") if l.strip()]
    first_title = "Document Analysis"
    for l in lines:
        if l.startswith("# "):
            first_title = l.lstrip("# ").strip()
            break
            
    word_count = len(markdown_text.split())
    
    return {
        "dashboard_title": first_title,
        "executive_summary": f"Document analyzed successfully ({word_count} words processed).",
        "kpis": [
            {"label": "Total Words", "value": f"{word_count:,}", "page_range": "Page 1"},
            {"label": "Status", "value": "Extracted", "page_range": "Page 1"}
        ],
        "key_value_pairs": extract_local_key_value_pairs(markdown_text),
        "keywords": extract_local_keywords(markdown_text),
        "charts": extract_charts_from_markdown_tables(markdown_text)
    }
