from fastapi import UploadFile
import pymupdf
import logging

logger = logging.getLogger(__name__)

def parse_image(file: UploadFile) -> dict:
    """
    Opens uploaded image files (.png, .jpg, .jpeg, .webp, .tiff) using PyMuPDF (fitz)
    and extracts text content.
    """
    file_bytes = file.file.read()
    file.file.seek(0)
    
    filename = file.filename.lower() if file.filename else "image.png"
    ext = filename.split(".")[-1]
    if ext in ["jpg", "jpeg"]:
        ext = "jpeg"
    elif ext not in ["png", "jpeg", "webp", "tiff", "tif"]:
        ext = "png"

    full_text = ""
    page_count = 1

    try:
        doc = pymupdf.open(stream=file_bytes, filetype=ext)
        page_count = len(doc)
        for page in doc:
            page_text = page.get_text()
            if page_text:
                full_text += page_text + "\n"
    except Exception as e:
        logger.warning(f"Error reading image stream with PyMuPDF: {e}")

    return {
        "text": full_text.strip(),
        "page_count": page_count,
        "file_bytes": file_bytes
    }
