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
    """
    contents = file.file.read()
    file.file.seek(0)
    
    full_text_pages = []
    page_count = 0
    
    try:
        import pymupdf
        doc = pymupdf.open(stream=contents, filetype="pdf")
        page_count = len(doc)
        ocr_engine = get_ocr_engine()
        
        for i, page in enumerate(doc):
            native_text = page.get_text().strip()
            images = page.get_images()
            
            ocr_text = ""
            # Trigger OCR if page has sparse/empty text (<20 chars) or contains embedded image blocks
            if (len(native_text) < 20 or len(images) > 0) and ocr_engine:
                try:
                    pix = page.get_pixmap(dpi=150)
                    result, _ = ocr_engine(pix.tobytes("png"))
                    if result:
                        ocr_text = " ".join([res[1] for res in result]).strip()
                except Exception as e:
                    logger.warning(f"OCR error on PDF page {i+1}: {e}")

            # Combine native text and OCR text cleanly without duplication
            page_content = native_text
            if ocr_text:
                if not page_content:
                    page_content = ocr_text
                elif ocr_text not in page_content and len(ocr_text) > len(page_content):
                    # Prefer OCR text if it captured more content than native text layer
                    page_content = native_text + "\n" + ocr_text

            if page_content:
                full_text_pages.append(f"--- Page {i+1} ---\n" + page_content)

        doc.close()
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
        "page_count": page_count
    }

