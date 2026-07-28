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
    model_name = os.getenv("VISION_MODEL_NAME", "meta/llama-3.2-11b-vision-instruct")
    
    ext = os.path.splitext(file.filename or "")[1] or ".pdf"
    
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        tmp.write(contents)
        tmp_path = tmp.name
        
    try:
        from engine.vision_client import is_vision_api_disabled
        if not api_key or is_vision_api_disabled():
            raise Exception("NVIDIA Vision API disabled or API key missing")

        from vision_parse import VisionParser
        import vision_parse.llm as vp_llm
        
        # Dynamically register NVIDIA NIM / OpenAI-compatible model strings into vision-parse lookup table
        if model_name not in vp_llm.SUPPORTED_MODELS:
            vp_llm.SUPPORTED_MODELS[model_name] = "openai"

        # Pass base_url via openai_config dictionary to avoid kwargs passing to completions.create
        parser = VisionParser(
            model_name=model_name,
            api_key=api_key,
            openai_config={"OPENAI_BASE_URL": base_url}
        )
        
        # vision-parse convert_pdf extracts PDF pages to a list of Markdown strings
        markdown_pages = parser.convert_pdf(pdf_path=tmp_path)
        
        page_count = len(markdown_pages) if isinstance(markdown_pages, list) else 1
        combined_text = "\n\n".join(
            f"--- Page {i+1} ---\n{page_md}" for i, page_md in enumerate(markdown_pages)
        ) if isinstance(markdown_pages, list) else str(markdown_pages)
        
        return {
            "text": combined_text,
            "page_count": page_count,
            "structured_tsv": None
        }
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
