import json
import os
import re
import logging
from collections import Counter
from openai import OpenAI

logger = logging.getLogger(__name__)

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
    Analyze the provided document markdown (including its embedded tables, equations, and key facts) 
    and synthesize a structured dashboard specification.

    Output STRICTLY a valid JSON object matching this schema:
    {
      "dashboard_title": "Descriptive Document Title",
      "executive_summary": "2-3 sentence overview of core findings and key highlights",
      "kpis": [
        {"label": "Metric Name", "value": "Formatted Value (e.g. $4.2M, 904 Words, 12 Pages, 15%)"}
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
          "y_data": [100, 200]
        }
      ]
    }
    Rules:
    - Extract real quantitative values from tables and text.
    - Extract 10-15 dominant domain keywords with relevance scores from 0.40 to 0.98.
    - If numbers exist in tables, construct at least 1-2 visual charts (bar, line, or pie).
    - Ensure x_data and y_data arrays match in length and contain numbers in y_data.
    - Output ONLY raw valid JSON. Do not write markdown codeblock wrappers like ```json.
    """

    input_context = markdown_text[:25000] if len(markdown_text) > 25000 else markdown_text

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
        if not parsed_spec.get("keywords"):
            parsed_spec["keywords"] = extract_local_keywords(markdown_text)
        if not parsed_spec.get("charts"):
            parsed_spec["charts"] = extract_charts_from_markdown_tables(markdown_text)
        return parsed_spec

    except Exception as exc:
        logger.error(f"Error calling NVIDIA DeepSeek-V4-Flash model: {exc}")
        return generate_heuristic_fallback_dashboard_spec(markdown_text)

def extract_charts_from_markdown_tables(markdown_text: str) -> list:
    """
    Parses Markdown grid tables (| Col 1 | Col 2 |) and converts numerical columns into visual chart objects.
    """
    charts = []
    lines = markdown_text.split("\n")
    table_blocks = []
    current_table = []

    for line in lines:
        if "|" in line and not line.strip().startswith(">"):
            current_table.append(line.strip())
        else:
            if len(current_table) >= 3:
                table_blocks.append(current_table)
            current_table = []

    if len(current_table) >= 3:
        table_blocks.append(current_table)

    for idx, block in enumerate(table_blocks):
        try:
            headers = [c.strip() for c in block[0].strip("|").split("|")]
            if len(headers) < 2:
                continue

            data_rows = []
            for row_line in block[2:]:
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
                    "y_data": y_data
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
            {"label": "Total Words", "value": f"{word_count:,}"},
            {"label": "Status", "value": "Extracted"}
        ],
        "keywords": extract_local_keywords(markdown_text),
        "charts": extract_charts_from_markdown_tables(markdown_text)
    }
