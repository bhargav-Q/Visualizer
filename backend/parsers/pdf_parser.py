from fastapi import UploadFile
import io
import logging

logger = logging.getLogger(__name__)

# Lazy load RapidOCR engine singleton
_ocr_engine = None

def get_ocr_engine():
    global _ocr_engine
    from engine.vision_client import is_vision_api_disabled
    if is_vision_api_disabled():
        return None

    if _ocr_engine is None:
        try:
            from rapidocr_onnxruntime import RapidOCR
            _ocr_engine = RapidOCR()
        except Exception as e:
            logger.warning(f"Could not load RapidOCR engine: {e}")
            _ocr_engine = False
    return _ocr_engine if _ocr_engine is not False else None

def process_page_parallel(job: dict) -> dict:
    """
    Parallel worker task for processing a single PDF page:
    1. Reads native text and spatial bounding boxes.
    2. Runs RapidOCR scanning on the page bitmap if OCR engine is active.
    3. Merges spatial grid output cleanly.
    """
    page_num = job["page_num"]
    native_text = job["native_text"]
    blocks = job["blocks"]
    png_bytes = job.get("png_bytes")
    ocr_engine = job.get("ocr_engine")
    
    ocr_text = ""
    grid_rows = []
    page_blocks = blocks

    if ocr_engine and png_bytes:
        try:
            from parsers.spatial_grid import filter_ocr_results_by_confidence, reconstruct_grid_from_ocr
            # RapidOCR call on PNG bytes
            raw_ocr = ocr_engine(png_bytes)
            if raw_ocr and isinstance(raw_ocr, (list, tuple)) and len(raw_ocr) > 0:
                results = raw_ocr[0] if isinstance(raw_ocr[0], list) else raw_ocr
                filtered = filter_ocr_results_by_confidence(results)
                if filtered:
                    grid_rows, tsv_output = reconstruct_grid_from_ocr(filtered)
                    ocr_text = tsv_output.strip()
                    
                    if len(blocks) < 2:
                        ocr_blocks = []
                        scale = 72.0 / 150.0
                        for item in filtered:
                            box, text_val = item[0], item[1]
                            if text_val and str(text_val).strip():
                                xs = [pt[0] * scale for pt in box]
                                ys = [pt[1] * scale for pt in box]
                                ocr_blocks.append({
                                    "bbox": [round(min(xs), 2), round(min(ys), 2), round(max(xs), 2), round(max(ys), 2)],
                                    "text": str(text_val).strip()
                                })
                        page_blocks = ocr_blocks
        except Exception as e:
            logger.warning(f"Parallel OCR error on PDF page {page_num}: {e}")

    # Combine native text and OCR text cleanly without duplication
    page_content = native_text
    if ocr_text:
        if not page_content:
            page_content = ocr_text
        elif ocr_text not in page_content and len(ocr_text) > len(page_content):
            page_content = native_text + "\n" + ocr_text

    return {
        "page_num": page_num,
        "page_content": page_content,
        "ocr_tsv": ocr_text,
        "blocks": page_blocks
    }

def parse_pdf(file: UploadFile) -> dict:
    """
    Reads an uploaded .pdf file and processes EVERY page in parallel.
    Uses ThreadPoolExecutor to run native text extraction & RapidOCR scanning 
    simultaneously across all available CPU cores.
    """
    file.file.seek(0)
    contents = file.file.read()
    file.file.seek(0)

    full_text_pages = []
    structured_tsv_pages = []
    page_blocks_by_page = {}
    page_count = 0

    try:
        import pymupdf
        doc = pymupdf.open(stream=contents, filetype="pdf")
        page_count = len(doc)
        ocr_engine = get_ocr_engine()

        extracted_tables = []
        page_jobs = []
        for i, page in enumerate(doc):
            page_num = i + 1
            native_text = page.get_text().strip()

            # 1. PyMuPDF Native Table Extraction
            try:
                tabs = page.find_tables()
                if tabs and len(tabs.tables) > 0:
                    for tab in tabs.tables:
                        df = tab.extract()
                        if df and len(df) >= 2:
                            headers = [str(h).strip() if h else f"Column_{idx+1}" for idx, h in enumerate(df[0])]
                            rows = []
                            for r in df[1:]:
                                if any(cell is not None and str(cell).strip() != "" for cell in r):
                                    clean_r = []
                                    for c in r:
                                        c_str = str(c).strip() if c is not None else ""
                                        clean_val = c_str.replace("$", "").replace(",", "").strip()
                                        try:
                                            num_val = float(clean_val) if "." in clean_val else int(clean_val)
                                            clean_r.append(num_val)
                                        except ValueError:
                                            clean_r.append(c_str)
                                    rows.append(clean_r)
                            if rows:
                                from contracts.document import TableData
                                extracted_tables.append(TableData(
                                    table_title=f"Extracted Table (Page {page_num})",
                                    headers=headers,
                                    rows=rows,
                                    page_number=page_num
                                ))
            except Exception as tab_err:
                logger.warning(f"PyMuPDF find_tables error on page {page_num}: {tab_err}")
            
            blocks = []
            text_instances = page.get_text("blocks")
            for b in text_instances:
                if len(b) >= 5 and b[4].strip():
                    blocks.append({
                        "bbox": [round(float(b[0]), 2), round(float(b[1]), 2), round(float(b[2]), 2), round(float(b[3]), 2)],
                        "text": b[4].strip()
                    })

            # Render PNG bitmap for parallel OCR scanning
            pix = page.get_pixmap(dpi=150)
            png_bytes = pix.tobytes("png")

            page_jobs.append({
                "page_num": page_num,
                "native_text": native_text,
                "blocks": blocks,
                "png_bytes": png_bytes,
                "ocr_engine": ocr_engine
            })
        
        doc.close()

        # Execute parallel page processing using system worker threadpool
        from processors.resource_manager import get_global_executor, collect_garbage
        executor = get_global_executor()
        
        results = list(executor.map(process_page_parallel, page_jobs))
        collect_garbage()

        # Re-sort results by page number to maintain exact document order
        results.sort(key=lambda r: r["page_num"])

        for r in results:
            p_num = r["page_num"]
            page_blocks_by_page[p_num] = r["blocks"]
            if r["ocr_tsv"]:
                structured_tsv_pages.append(r["ocr_tsv"])
            if r["page_content"]:
                full_text_pages.append(f"--- Page {p_num} ---\n" + r["page_content"])

        # Deduplicate repeated header lines from digital text pages across multi-page PDFs
        if len(full_text_pages) > 1:
            from collections import Counter
            all_lines = []
            for page_block in full_text_pages:
                for line in page_block.split("\n"):
                    stripped = line.strip()
                    if stripped and not stripped.startswith("--- Page"):
                        all_lines.append(stripped)
            line_counts = Counter(all_lines)
            repeated_headers = set()
            for line_text, count in line_counts.items():
                if count >= 3 and ("|" in line_text or "\t" in line_text):
                    repeated_headers.add(line_text)
            if repeated_headers:
                deduped_pages = []
                first_occurrence = set()
                for page_block in full_text_pages:
                    lines = page_block.split("\n")
                    filtered = []
                    for line in lines:
                        stripped = line.strip()
                        if stripped in repeated_headers:
                            if stripped not in first_occurrence:
                                first_occurrence.add(stripped)
                                filtered.append(line)
                        else:
                            filtered.append(line)
                    deduped_pages.append("\n".join(filtered))
                full_text_pages = deduped_pages

    except Exception as e:
        logger.warning(f"PyMuPDF parse error: {e}, falling back to pypdf...")
        try:
            import pypdf
            reader = pypdf.PdfReader(io.BytesIO(contents))
            page_count = len(reader.pages)
            for i, page in enumerate(reader.pages):
                extracted = page.extract_text()
                if extracted:
                    full_text_pages.append(extracted)
        except Exception as pypdf_err:
            logger.error(f"pypdf fallback error: {pypdf_err}")

    full_text = "\n".join(full_text_pages)
    tsv_text = "\n".join(structured_tsv_pages)

    # Fallback to parse_tsv_grid if no tables extracted yet
    if not extracted_tables:
        from processors.ocr_processor import parse_tsv_grid
        from contracts.document import TableData
        grid = parse_tsv_grid(tsv_text) or parse_tsv_grid(full_text)
        if grid:
            extracted_tables.append(TableData(
                table_title="Extracted Table Grid",
                headers=grid["headers"],
                rows=grid["rows"],
                page_number=1
            ))

    return {
        "text": full_text,
        "structured_tsv": tsv_text,
        "page_count": page_count,
        "blocks_by_page": page_blocks_by_page,
        "tables": extracted_tables
    }
