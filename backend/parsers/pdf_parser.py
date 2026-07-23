from fastapi import UploadFile
import io
import logging

logger = logging.getLogger(__name__)

# Lazy load RapidOCR engine singleton
_ocr_engine = None

def get_ocr_engine():
    global _ocr_engine
    if _ocr_engine is None:
        try:
            from rapidocr_onnxruntime import RapidOCR
            _ocr_engine = RapidOCR()
        except Exception as e:
            logger.warning(f"Could not load RapidOCR engine: {e}")
            _ocr_engine = False
    return _ocr_engine if _ocr_engine is not False else None

def parse_pdf(file: UploadFile) -> dict:
    """
    Reads an uploaded .pdf file and extracts text and metadata.
    Uses PyMuPDF for native digital text and automatically triggers
    RapidOCR pixmap scanning for scanned pages or pages with embedded images.
    Applies spatial bounding-box grid reconstruction and multi-page header deduplication.
    """
    file.file.seek(0)
    contents = file.file.read()
    file.file.seek(0)

    
    full_text_pages = []
    structured_tsv_pages = []
    page_count = 0
    canonical_header_line = None
    
    try:
        import pymupdf
        doc = pymupdf.open(stream=contents, filetype="pdf")
        page_count = len(doc)
        ocr_engine = get_ocr_engine()
        
        # Process pages in controlled chunks of 5 pages to prevent RAM spikes
        from processors.resource_manager import chunk_list, collect_garbage

        for chunk_idx, page_chunk in enumerate(chunk_list(list(doc), chunk_size=5)):
            for offset, page in enumerate(page_chunk):
                i = chunk_idx * 5 + offset
                native_text = page.get_text().strip()
                images = page.get_images()
                
                ocr_text = ""
                grid_rows = []
                
                # Trigger OCR if page has sparse/empty text (<50 chars) OR embedded images
                if (len(native_text) < 50 or len(images) > 0) and ocr_engine:
                    try:
                        from parsers.spatial_grid import reconstruct_grid_from_ocr, run_ocr_with_orientation_check
                        results = run_ocr_with_orientation_check(page, ocr_engine, dpi=150)
                        if results:
                            grid_rows, tsv_output = reconstruct_grid_from_ocr(results)
                            
                            # Multi-page Header Deduplication
                            if grid_rows:
                                first_line = "\t".join(grid_rows[0]).strip()
                                if canonical_header_line is None:
                                    canonical_header_line = first_line
                                elif first_line == canonical_header_line:
                                    # Drop duplicate header row on subsequent pages
                                    grid_rows = grid_rows[1:]
                                    tsv_output = "\n".join(["\t".join(r) for r in grid_rows])

                            ocr_text = tsv_output.strip()
                    except Exception as e:
                        logger.warning(f"OCR error on PDF page {i+1}: {e}")

                # Combine native text and OCR text cleanly without duplication
                page_content = native_text
                if ocr_text:
                    if not page_content:
                        page_content = ocr_text
                    elif ocr_text not in page_content and len(ocr_text) > len(page_content):
                        page_content = native_text + "\n" + ocr_text
                    structured_tsv_pages.append(ocr_text)

                if page_content:
                    full_text_pages.append(f"--- Page {i+1} ---\n" + page_content)

            # Release bitmap RAM memory after each 5-page chunk
            collect_garbage()

        doc.close()

        # Problem 3 Fix: Deduplicate repeated header lines from digital text pages.
        # Multi-page PDFs often repeat the same table header row on every page.
        if len(full_text_pages) > 1:
            from collections import Counter
            all_lines = []
            for page_block in full_text_pages:
                for line in page_block.split("\n"):
                    stripped = line.strip()
                    if stripped and not stripped.startswith("--- Page"):
                        all_lines.append(stripped)
            line_counts = Counter(all_lines)
            # A header is a line that appears on 3+ pages and contains separator chars
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
                            # else: skip duplicate header
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

    return {
        "text": "\n\n".join(full_text_pages),
        "structured_tsv": "\n".join(structured_tsv_pages),
        "page_count": page_count
    }

