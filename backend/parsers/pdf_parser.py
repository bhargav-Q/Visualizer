from fastapi import UploadFile
import io
import logging

logger = logging.getLogger(__name__)

# Lazy load RapidOCR engine singleton
_ocr_engine = None

def get_ocr_engine():
    """Lazy load RapidOCR engine singleton if available."""
    global _ocr_engine
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
                        scale = 72.0 / 350.0
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
    used_source = "native_text"
    if ocr_text:
        if not page_content:
            page_content = ocr_text
            used_source = "ocr_text"
        elif ocr_text not in page_content and len(ocr_text) > len(page_content):
            page_content = native_text + "\n" + ocr_text
            used_source = "native_text + ocr_text"

    logger.info(f"[OCR_DEBUG] process_page_parallel Page {page_num}: used {used_source} (native_text_len={len(native_text)}, ocr_text_len={len(ocr_text)}, page_content_len={len(page_content)})")

    return {
        "page_num": page_num,
        "page_content": page_content,
        "ocr_tsv": ocr_text,
        "blocks": page_blocks
    }

def parse_pdf(file: UploadFile) -> dict:
    """
    Reads an uploaded .pdf file and processes it via the official Mistral OCR API using Base64 Data URLs.
    Eliminates manual bounding box slicing and hard character truncation bottlenecks.
    Falls back to PyMuPDF native text if API is unavailable.
    """
    file.file.seek(0)
    contents = file.file.read()
    file.file.seek(0)

    filename = file.filename or "document.pdf"

    # 1. Primary: Official Mistral OCR API via Base64 Data URL
    try:
        from services.mistral_ocr_service import process_document_with_mistral_ocr
        ocr_res = process_document_with_mistral_ocr(
            file_bytes=contents,
            filename=filename
        )
        if ocr_res and ocr_res.get("markdown_text"):
            return {
                "text": ocr_res["markdown_text"],
                "structured_tsv": "",
                "page_count": ocr_res.get("page_count", 1),
                "blocks_by_page": {},
                "tables": []
            }
    except Exception as exc:
        logger.warning(f"Mistral OCR primary route failed: {exc}. Executing PyMuPDF native fallback...")

    # 2. Fallback: PyMuPDF Native Extraction
    full_text_pages = []
    page_count = 0
    try:
        import pymupdf
        doc = pymupdf.open(stream=contents, filetype="pdf")
        page_count = len(doc)
        for i, page in enumerate(doc):
            page_text = page.get_text().strip()
            if page_text:
                full_text_pages.append(f"--- Page {i+1} ---\n" + page_text)
        doc.close()
    except Exception as e:
        logger.warning(f"PyMuPDF fallback error: {e}")

    full_text = "\n\n".join(full_text_pages)
    return {
        "text": full_text,
        "structured_tsv": "",
        "page_count": page_count,
        "blocks_by_page": {},
        "tables": []
    }
