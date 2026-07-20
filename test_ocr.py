import os
import sys
import time
import json
import base64
from dotenv import load_dotenv

# Load environment variables
load_dotenv(r"c:\Users\bharg\python work\Visualizer\.env")
api_key = os.getenv("NVIDIA_API_KEY")

def step_1_script_based_extraction(pdf_path: str) -> dict | None:
    """
    Step 1: Fast, deterministic local script-based table extraction using pdfplumber.
    Enhanced with Header Resolver, Row Density Filtering, and Quality Gatekeeper.
    Returns {headers: [...], rows: [[...], ...]} or None if Quality Gatekeeper fails.
    """
    import pdfplumber

    HEADER_KEYWORDS = ["CODE", "CLASS", "DESCR", "CATEGORIES", "DUTIES", "EMPLOYEES", "PAYROLL", "PREMIUM", "RATE", "SIC", "NAICS", "AMOUNT", "TOTAL", "DATE", "MONTH"]

    try:
        with pdfplumber.open(pdf_path) as pdf:
            all_tables = []
            for page in pdf.pages:
                tables = page.extract_tables()
                for t in tables:
                    if t and len(t) > 1: # Must have at least 1 header row + 1 data row
                        all_tables.append(t)
            
            if not all_tables:
                return None
            
            # Use the largest table found
            raw_table = max(all_tables, key=len)
            
            # --- 1. HEADER RESOLVER ---
            header_row_idx = 0
            # Check if row 0 is a Title Block (e.g. Form Title like "STATE RATING WORKSHEET...")
            first_row_str = " ".join([str(c) for c in raw_table[0] if c]).upper()
            if len(first_row_str) > 40 or any(title_word in first_row_str for title_word in ["WORKSHEET", "RATING", "FORM", "STATE RATING", "SECTION"]):
                # Look for the true header row in the first 3 rows
                for idx in range(min(3, len(raw_table))):
                    candidate_str = " ".join([str(c) for c in raw_table[idx] if c]).upper()
                    if any(kw in candidate_str for kw in HEADER_KEYWORDS):
                        header_row_idx = idx
                        break

            # Extract headers
            raw_headers = raw_table[header_row_idx]
            headers = []
            for i, cell in enumerate(raw_headers):
                cell_text = str(cell).strip().replace("\n", " ") if cell else ""
                headers.append(cell_text if cell_text else f"Column_{i+1}")

            # --- 2. ROW DENSITY FILTER ---
            data_rows = raw_table[header_row_idx + 1:]
            clean_rows = []
            total_cells_checked = 0
            non_null_cells_checked = 0

            for row in data_rows:
                # Count non-empty cells in this row
                non_empty_count = sum(1 for val in row if val is not None and str(val).strip() != "")
                
                # Filter out empty box outline rows (must have at least 2 non-empty cells)
                if non_empty_count < 2:
                    continue

                clean_row = []
                for val in row:
                    total_cells_checked += 1
                    if val is None:
                        clean_row.append(None)
                    else:
                        str_val = str(val).strip().replace("\n", " ")
                        if str_val == "":
                            clean_row.append(None)
                        else:
                            non_null_cells_checked += 1
                            # Clean numeric strings ($1,234.50 -> 1234.5)
                            clean_num = str_val.replace("$", "").replace(",", "").replace("%", "")
                            try:
                                if "." in clean_num:
                                    clean_row.append(float(clean_num))
                                else:
                                    clean_row.append(int(clean_num))
                            except ValueError:
                                clean_row.append(str_val)
                clean_rows.append(clean_row)

            # --- 3. QUALITY GATEKEEPER ---
            # Check 1: Do we have at least 1 clean data row?
            if not clean_rows or len(clean_rows) < 1:
                print("   [Gatekeeper Note] Step 1 rejected: 0 valid data rows found after density filtering.")
                return None

            # Check 2: Cell Density Check — if > 65% of cells are empty nulls, it's a form outline
            density = (non_null_cells_checked / total_cells_checked) if total_cells_checked > 0 else 0
            if density < 0.35:
                print(f"   [Gatekeeper Note] Step 1 rejected: Low cell density ({density*100:.1f}% non-null cells). Form outlines detected.")
                return None

            # Check 3: Header Sanity Check — if Header 1 still looks like a massive title block
            if len(headers[0]) > 45:
                print("   [Gatekeeper Note] Step 1 rejected: Header 1 contains unparsed title block.")
                return None

            return {
                "headers": headers,
                "rows": clean_rows
            }

    except Exception as e:
        print(f"   [Step 1 Note] Local script extraction notice: {e}")
    
    return None


def step_2_deepseek_ai_fallback(pdf_path: str) -> dict | None:
    """
    Step 2: Fallback to deepseek-ai/deepseek-v4-flash AI model if Step 1 yields no table.
    Extracts text/image and uses AI prompt engineering to reconstruct messy/complex/scanned tables.
    """
    import pymupdf
    from openai import OpenAI

    if not api_key:
        print("   [Step 2 Error] NVIDIA_API_KEY missing from .env")
        return None

    # Extract text from PDF
    doc = pymupdf.open(pdf_path)
    full_text = ""
    for page in doc:
        full_text += page.get_text() + "\n"
    
    if not full_text.strip():
        print("   [Step 2 Note] No text in PDF, document might be a pure scanned image.")
        return None

    client = OpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=api_key
    )

    prompt = f"""You are a tabular data extraction expert. Analyze the following document text and extract any tabular data into structured JSON.

Return ONLY this JSON structure:
{{
  "has_table": true,
  "headers": ["Column1", "Column2", "Column3"],
  "rows": [
    ["value1", 100, 45.5],
    ["value2", 200, 90.0]
  ]
}}

Rules:
- Convert numeric values to numbers (e.g. "$1,234" -> 1234, "45.6%" -> 45.6).
- Keep dates and strings as text.
- If there is NO tabular data, return: {{"has_table": false, "headers": [], "rows": []}}

Document Text:
{full_text[:6000]}"""

    try:
        completion = client.chat.completions.create(
            model="deepseek-ai/deepseek-v4-flash",
            messages=[{"role": "user", "content": prompt}],
            temperature=1,
            max_tokens=8192,
            extra_body={"chat_template_kwargs": {"thinking": True, "reasoning_effort": "high"}},
            response_format={"type": "json_object"},
            timeout=45.0
        )
        
        # Print reasoning if available
        reasoning = getattr(completion.choices[0].message, "reasoning", None) or getattr(completion.choices[0].message, "reasoning_content", None)
        if reasoning:
            print("\n   [DeepSeek AI Reasoning]:")
            print("   " + "\n   ".join(reasoning.strip().split("\n")[:8]) + "...\n")

        content = completion.choices[0].message.content.strip()
        if content.startswith("```"):
            lines = content.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            content = "\n".join(lines)

        data = json.loads(content)
        if data.get("has_table") and data.get("headers") and data.get("rows"):
            return {
                "headers": data["headers"],
                "rows": data["rows"]
            }
    except Exception as e:
        print(f"   [Step 2 Error] DeepSeek AI parsing error: {e}")

    return None


def run_hybrid_ocr_pipeline(pdf_path: str):
    print("=" * 65)
    print(f"[RUNNING] HYBRID OCR PIPELINE ON: {os.path.basename(pdf_path)}")
    print("=" * 65)

    start_time = time.time()

    # --- STEP 1: Script-Based Local Extraction ---
    print("\n[STEP 1] Executing Script-Based Local Table Extraction (pdfplumber)...")
    step1_start = time.time()
    result = step_1_script_based_extraction(pdf_path)
    step1_duration = time.time() - step1_start

    if result:
        total_duration = time.time() - start_time
        print(f"[SUCCESS] Step 1 (Script-Based Local)!")
        print(f"Timing: Step 1 Duration: {step1_duration:.3f} seconds (API Cost: $0.00)")
        print(f"Stats: Extracted {len(result['headers'])} Columns, {len(result['rows'])} Rows")
        print("\n--- STRUCTURED TABLE JSON OUTPUT ---")
        print(json.dumps(result, indent=2))
        print("=" * 65)
        return

    print(f"[NOTE] Step 1 returned no valid table ({step1_duration:.3f}s). Passing to Step 2 AI Fallback...")

    # --- STEP 2: DeepSeek AI Fallback for Uncompleted Work ---
    print("\n[STEP 2] Executing DeepSeek AI Fallback (deepseek-v4-flash)...")
    step2_start = time.time()
    result = step_2_deepseek_ai_fallback(pdf_path)
    step2_duration = time.time() - step2_start
    total_duration = time.time() - start_time

    if result:
        print(f"[SUCCESS] Step 2 (DeepSeek AI Fallback)!")
        print(f"Timing: Step 2 Duration: {step2_duration:.2f} seconds | Total Time: {total_duration:.2f}s")
        print(f"Stats: Extracted {len(result['headers'])} Columns, {len(result['rows'])} Rows")
        print("\n--- STRUCTURED TABLE JSON OUTPUT ---")
        print(json.dumps(result, indent=2))
    else:
        print(f"[FAIL] No tabular data found in either Step 1 or Step 2 (Total Time: {total_duration:.2f}s)")
    
    print("=" * 65)


if __name__ == "__main__":
    target_pdf = sys.argv[1] if len(sys.argv) > 1 else r"c:\Users\bharg\python work\Visualizer\backend\test_table.pdf"
    
    # Generate a dummy test table PDF if target doesn't exist
    if not os.path.exists(target_pdf):
        print(f"Creating sample test PDF at {target_pdf}...")
        import pymupdf
        doc = pymupdf.open()
        page = doc.new_page()
        page.insert_text((50, 50), "Quarterly Financial Report", fontsize=16)
        page.insert_text((50, 80), "Month\tRevenue\tExpenses", fontsize=12)
        page.insert_text((50, 100), "January\t$10,000\t$8,000", fontsize=11)
        page.insert_text((50, 120), "February\t$12,500\t$9,200", fontsize=11)
        page.insert_text((50, 140), "March\t$15,000\t$10,100", fontsize=11)
        doc.save(target_pdf)

    run_hybrid_ocr_pipeline(target_pdf)
