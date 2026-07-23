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
    import time
    import concurrent.futures
    from engine.vision_client import extract_analytics_with_vision

    t_start = time.perf_counter()
    page_text_blocks_by_page = {}
    full_text_pages = []
    page_pngs = []

    try:
        doc = pymupdf.open(stream=contents, filetype="pdf")
        for i, page in enumerate(doc):
            page_num = i + 1
            
            # Render page to PNG for Vision LLM payload
            pix = page.get_pixmap(dpi=150)
            png_bytes = pix.tobytes("png")
            page_pngs.append((page_num, png_bytes, page.get_text().strip()))

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
                t_ocr_start = time.perf_counter()
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
                    logger.info(f"[PROFILER] Page {page_num} OCR fallback elapsed time: {time.perf_counter() - t_ocr_start:.4f}s")
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
    logger.info(f"[PROFILER] Native PDF Text & Spatial Blocks Extraction: {time.perf_counter() - t_start:.4f}s")

    # 2. Parallel Vision LLM page batching extraction
    t_vision_start = time.perf_counter()
    
    def process_page_vision(p_num, png, text_hint):
        try:
            return p_num, extract_analytics_with_vision(png, text_hint=text_hint[:3000])
        except Exception as vision_err:
            logger.warning(f"Parallel Vision LLM call failed for page {p_num}: {vision_err}")
            return p_num, None

    results = []
    if page_pngs:
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(page_pngs), 2)) as pool:
            futures = {
                pool.submit(process_page_vision, p_num, png, txt): p_num
                for p_num, png, txt in page_pngs
            }
            for future in concurrent.futures.as_completed(futures):
                p_num = futures[future]
                try:
                    p_num, page_an = future.result()
                    if page_an:
                        results.append((p_num, page_an))
                except Exception as exc:
                    logger.warning(f"Page {p_num} vision thread generated exception: {exc}")

    # Sort results by page number to keep order
    results.sort(key=lambda x: x[0])
    
    logger.info(f"[PROFILER] Parallel Vision LLM page batching runtime: {time.perf_counter() - t_vision_start:.4f}s")

    # Merge results
    analytics = None
    if results:
        # Use first page's document_title and report_date as anchor details
        first_p, first_an = results[0]
        
        # Combine summaries
        summaries = []
        for p_num, an in results:
            if an.summary and an.summary.strip():
                summaries.append(f"[Page {p_num}] {an.summary.strip()}")
        combined_summary = "\n\n".join(summaries) if summaries else first_an.summary

        # Union keywords
        keywords_set = set()
        for p_num, an in results:
            if an.keywords:
                keywords_set.update(an.keywords)

        # Merge metrics, key_value_pairs, and tables (assigning/updating page number mapping)
        merged_metrics = []
        merged_kv_pairs = []
        merged_tables = []

        for p_num, an in results:
            if an.metrics:
                for m in an.metrics:
                    m.page_number = p_num
                    merged_metrics.append(m)
            if an.key_value_pairs:
                for kv in an.key_value_pairs:
                    kv.page_number = p_num
                    merged_kv_pairs.append(kv)
            if an.tables:
                for tbl in an.tables:
                    tbl.page_number = p_num
                    merged_tables.append(tbl)

        analytics = DocumentAnalytics(
            document_title=first_an.document_title or "Untitled Document",
            report_date=first_an.report_date,
            summary=combined_summary,
            keywords=list(keywords_set),
            metrics=merged_metrics,
            key_value_pairs=merged_kv_pairs,
            tables=merged_tables
        )
    else:
        # Fallback to local heuristics if no vision calls returned valid results
        logger.warning("[WARNING] No Vision LLM responses received. Executing heuristic fallback parsing.")
        analytics = create_heuristic_fallback_analytics(filename, raw_combined_text)

    # 3. Match metrics to bounding boxes
    t_match_start = time.perf_counter()
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
    logger.info(f"[PROFILER] Spatial Bounding Box Match Heuristics: {time.perf_counter() - t_match_start:.4f}s")

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
