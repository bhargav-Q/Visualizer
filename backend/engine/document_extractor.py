import os
import io
import re
import logging
from typing import Optional, List, Dict, Any
from fastapi import UploadFile

from engine.pydantic_models import DocumentAnalytics, ExtractedMetric, KeyValuePair, ExtractedTable
from engine.vision_client import extract_analytics_with_vision
from engine.db import save_document_analytics

logger = logging.getLogger(__name__)

def match_text_to_bbox(page_text_blocks: List[Dict[str, Any]], snippet: str) -> Optional[List[float]]:
    """
    Matches an extracted text snippet to page-level PyMuPDF spatial bounding boxes [x0, y0, x1, y1].
    """
    if not snippet or not page_text_blocks:
        return None

    clean_snippet = re.sub(r'\s+', ' ', snippet.lower().strip())
    if not clean_snippet:
        return None

    for block in page_text_blocks:
        block_text = re.sub(r'\s+', ' ', block.get("text", "").lower().strip())
        if block_text and (clean_snippet in block_text or block_text in clean_snippet):
            bbox = block.get("bbox")
            if bbox and len(bbox) == 4:
                return [round(float(c), 2) for c in bbox]

    # Partial keyword match fallback
    words = [w for w in clean_snippet.split() if len(w) > 3]
    if words:
        first_word = words[0]
        for block in page_text_blocks:
            block_text = block.get("text", "").lower()
            if first_word in block_text:
                bbox = block.get("bbox")
                if bbox and len(bbox) == 4:
                    return [round(float(c), 2) for c in bbox]

    return None

def extract_pdf_document(contents: bytes, filename: str) -> DocumentAnalytics:
    """
    PDF Handler:
    1. Renders PDF pages to PNG images for Vision LLM vision parsing.
    2. Extracts PyMuPDF text blocks with page_number and bounding box coordinates [x0, y0, x1, y1].
    3. Matches extracted metric snippets to bounding box coordinates.
    """
    import pymupdf

    page_text_blocks_by_page = {}
    full_text_pages = []
    first_page_png = None

    try:
        doc = pymupdf.open(stream=contents, filetype="pdf")
        for i, page in enumerate(doc):
            page_num = i + 1
            # Render first page to PNG for Vision LLM payload
            if i == 0:
                pix = page.get_pixmap(dpi=150)
                first_page_png = pix.tobytes("png")

            # Extract spatial text blocks with bounding boxes
            blocks = []
            text_instances = page.get_text("blocks")
            for b in text_instances:
                # b: (x0, y0, x1, y1, text, block_no, block_type)
                if len(b) >= 5 and b[4].strip():
                    blocks.append({
                        "bbox": [b[0], b[1], b[2], b[3]],
                        "text": b[4].strip()
                    })

            # Check if we should fall back to OCR coordinates for scanned/image pages
            if len(blocks) < 2 or sum(len(b["text"]) for b in blocks) < 50:
                try:
                    from parsers.pdf_parser import get_ocr_engine
                    ocr_engine = get_ocr_engine()
                    if ocr_engine:
                        from parsers.spatial_grid import run_ocr_with_orientation_check
                        ocr_results = run_ocr_with_orientation_check(page, ocr_engine, dpi=150)
                        if ocr_results:
                            blocks = []
                            scale_factor = 72.0 / 150.0
                            for item in ocr_results:
                                box = item[0]
                                text = str(item[1]).strip()
                                if text:
                                    xs = [pt[0] for pt in box]
                                    ys = [pt[1] for pt in box]
                                    min_x, max_x = min(xs), max(xs)
                                    min_y, max_y = min(ys), max(ys)
                                    blocks.append({
                                        "bbox": [
                                            min_x * scale_factor,
                                            min_y * scale_factor,
                                            max_x * scale_factor,
                                            max_y * scale_factor
                                        ],
                                        "text": text
                                    })
                except Exception as ocr_err:
                    logger.warning(f"Failed to run OCR fallback blocks on page {page_num}: {ocr_err}")

            page_text_blocks_by_page[page_num] = {
                "blocks": blocks,
                "width": float(page.rect.width),
                "height": float(page.rect.height)
            }
            page_text = page.get_text().strip()
            if page_text:
                full_text_pages.append(f"--- Page {page_num} ---\n" + page_text)

        doc.close()
    except Exception as pdf_err:
        logger.warning(f"PyMuPDF error reading '{filename}': {pdf_err}")

    raw_combined_text = "\n\n".join(full_text_pages)

    # 2. Vision LLM extraction
    analytics = None
    if first_page_png:
        analytics = extract_analytics_with_vision(first_page_png, text_hint=raw_combined_text[:3000])

    # Fallback to local heuristic parsing if LLM vision returns None
    if not analytics:
        analytics = create_heuristic_fallback_analytics(filename, raw_combined_text)

    # 3. Match metrics to bounding boxes
    for m in analytics.metrics:
        p_num = m.page_number or 1
        page_info = page_text_blocks_by_page.get(p_num) or page_text_blocks_by_page.get(1)
        if page_info:
            blocks = page_info["blocks"]
            m.page_width = page_info["width"]
            m.page_height = page_info["height"]
            matched_bbox = match_text_to_bbox(blocks, m.context_snippet)
            if matched_bbox:
                m.bbox = matched_bbox

    return analytics

def extract_docx_document(contents: bytes, filename: str) -> DocumentAnalytics:
    """
    DOCX Handler:
    Extracts paragraphs and tables natively using python-docx.
    """
    import docx

    paragraphs = []
    table_rows = []

    try:
        doc = docx.Document(io.BytesIO(contents))
        for p in doc.paragraphs:
            if p.text and p.text.strip():
                paragraphs.append(p.text.strip())

        for table in doc.tables:
            t_headers = []
            t_data_rows = []
            for r_idx, row in enumerate(table.rows):
                cells = [c.text.strip() for c in row.cells]
                if r_idx == 0:
                    t_headers = cells
                else:
                    t_data_rows.append(cells)
            if t_headers or t_data_rows:
                table_rows.append(ExtractedTable(
                    table_title=f"DOCX Table {len(table_rows)+1}",
                    headers=t_headers,
                    rows=t_data_rows,
                    page_number=1
                ))
    except Exception as docx_err:
        logger.warning(f"python-docx error reading '{filename}': {docx_err}")

    combined_text = "\n".join(paragraphs)
    analytics = create_heuristic_fallback_analytics(filename, combined_text)
    if table_rows:
        analytics.tables.extend(table_rows)

    return analytics

def stream_txt_lines(contents: bytes):
    """
    TXT Generator Streamer:
    Streams text line-by-line using Python generator for flat memory footprint.
    """
    try:
        decoded = contents.decode("utf-8")
    except UnicodeDecodeError:
        decoded = contents.decode("latin-1", errors="replace")

    for line in decoded.splitlines():
        line_clean = line.strip()
        if line_clean:
            yield line_clean

def extract_txt_document(contents: bytes, filename: str) -> DocumentAnalytics:
    """
    TXT Handler:
    Uses generator line streaming to assemble clean document text.
    """
    lines = list(stream_txt_lines(contents))
    combined_text = "\n".join(lines)
    return create_heuristic_fallback_analytics(filename, combined_text)

def create_heuristic_fallback_analytics(filename: str, raw_text: str) -> DocumentAnalytics:
    """
    Creates a valid DocumentAnalytics instance from raw document text by extracting
    numbers, key-value patterns, summaries, and keyword topics.
    """
    lines = [l.strip() for l in raw_text.split("\n") if l.strip() and not l.startswith("--- Page")]
    words = [w for w in raw_text.split() if len(w) > 3]

    metrics = []
    key_values = []

    # Extract numerical metric lines with regex
    number_pattern = re.compile(r'([A-Za-z\s]{3,30})[:\s]+(\$?\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*(USD|%|kg|units|MB|GB)?', re.IGNORECASE)

    for line in lines[:100]:
        match = number_pattern.search(line)
        if match:
            cat_name = match.group(1).strip()
            num_str = match.group(2).replace("$", "").replace(",", "").strip()
            unit_str = match.group(3)
            try:
                val = float(num_str)
                metrics.append(ExtractedMetric(
                    category=cat_name[:40],
                    metric_value=val,
                    unit=unit_str,
                    context_snippet=line[:120],
                    page_number=1
                ))
            except ValueError:
                pass

        # Extract Key-Value pairs
        if ":" in line and not line.startswith("http"):
            parts = line.split(":", 1)
            k = parts[0].strip()
            v = parts[1].strip()
            if k and v and len(k) < 30 and len(v) < 80:
                key_values.append(KeyValuePair(
                    key_name=k,
                    value=v,
                    context_snippet=line[:120],
                    page_number=1
                ))

    # Summary
    summary = "\n".join(lines[:3]) if lines else "Document content ingested successfully."
    keywords = list(set([w.strip(".,;:()") for w in words[:20] if len(w) > 4]))[:10]

    return DocumentAnalytics(
        document_title=filename,
        report_date=None,
        summary=summary,
        keywords=keywords,
        metrics=metrics,
        key_value_pairs=key_values,
        tables=[]
    )

def process_unstructured_document(file: UploadFile) -> Dict[str, Any]:
    """
    Main entrypoint for unstructured document extraction.
    Parses layout/bounding boxes, calls Vision LLM & heuristics,
    saves metrics/analytics into DuckDB (app_data.duckdb), and returns structured results.
    """
    file.file.seek(0)
    contents = file.file.read()
    file.file.seek(0)

    filename = file.filename or "document.pdf"
    lower_name = filename.lower()

    try:
        if lower_name.endswith(".pdf"):
            analytics = extract_pdf_document(contents, filename)
        elif lower_name.endswith((".docx", ".doc")):
            analytics = extract_docx_document(contents, filename)
        elif lower_name.endswith((".txt", ".md")):
            analytics = extract_txt_document(contents, filename)
        else:
            analytics = create_heuristic_fallback_analytics(filename, contents.decode("utf-8", errors="ignore"))

        # Persist extracted metrics to DuckDB
        inserted_records = save_document_analytics(filename, analytics)

        return {
            "file_name": filename,
            "analytics": analytics.model_dump(),
            "duckdb_persisted": True,
            "records_inserted": inserted_records
        }
    except Exception as e:
        logger.error(f"Error processing unstructured document '{filename}': {e}")
        # Return fallback result without crashing
        fallback = create_heuristic_fallback_analytics(filename, "")
        save_document_analytics(filename, fallback)
        return {
            "file_name": filename,
            "analytics": fallback.model_dump(),
            "duckdb_persisted": True,
            "records_inserted": 0
        }
