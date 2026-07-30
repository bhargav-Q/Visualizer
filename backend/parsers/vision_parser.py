import os
import tempfile
import logging
from typing import Dict, Any
from fastapi import UploadFile
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

def parse_pdf_with_vision(file: UploadFile) -> Dict[str, Any]:
    """
    Dynamic PDF parser wrapping vision-parse VLM engine.
    Converts uploaded document stream dynamically into structured Markdown pages using VisionParser.
    """
    file.file.seek(0)
    contents = file.file.read()
    file.file.seek(0)
    
    api_key = os.getenv("NVIDIA_API_KEY")
    base_url = os.getenv("NVIDIA_NIM_BASE_URL", "https://integrate.api.nvidia.com/v1")
    model_name = os.getenv("VISION_MODEL_NAME", "mistral-ocr-latest")
    
    ext = os.path.splitext(file.filename or "")[1] or ".pdf"
    
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        tmp.write(contents)
        tmp_path = tmp.name
        
    try:
        from engine.vision_client import process_document_with_mistral_ocr
        md_res = process_document_with_mistral_ocr(document_bytes=contents)
        if md_res and md_res.strip():
            return {
                "text": md_res,
                "page_count": md_res.count("<!-- PAGE "),
                "structured_tsv": None
            }
        raise Exception("Mistral OCR returned empty result, using PyMuPDF text fallback")
    except Exception as e:
        logger.warning(f"vision-parse extraction fallback to basic PyMuPDF text: {e}")
        # Fallback to PyMuPDF native text if VLM API is rate-limited or errors out
        import pymupdf
        doc = pymupdf.open(stream=contents, filetype="pdf")
        page_count = len(doc)
        pages_text = [f"--- Page {i+1} ---\n" + page.get_text().strip() for i, page in enumerate(doc)]
        doc.close()
        return {
            "text": "\n\n".join(pages_text),
            "page_count": page_count,
            "structured_tsv": None
        }
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass
