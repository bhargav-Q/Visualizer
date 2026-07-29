from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import time
import asyncio
import logging

from models.schemas import UploadResponse
from parsers.xlsx_parser import parse_xlsx
from parsers.pdf_parser import parse_pdf
from parsers.vision_parser import parse_pdf_with_vision
from parsers.docx_parser import parse_docx
from parsers.txt_parser import parse_txt
from parsers.image_parser import parse_image
from engine.document_extractor import process_unstructured_document_async, merge_native_and_vision_data, merge_text_and_llm_data
from processors.tabular_processor import process_tabular_data
from processors.text_processor import process_text, process_text_async
from processors.ocr_processor import extract_tables_from_text, extract_tables_from_text_async, parse_tsv_grid
from models.schemas import TextResult
from config import MAX_FILE_SIZE_BYTES, DEFAULT_ALLOWED_ORIGINS, DEFAULT_PORT, DEFAULT_HOST, BACKEND_DIR, ROOT_DIR, DATA_DIR
from constants import QUANTITATIVE_SIGNALS

# Suppress harmless pdfminer warnings about fonts
logging.getLogger("pdfminer").setLevel(logging.ERROR)

logger = logging.getLogger(__name__)

from pathlib import Path
import os
DOCUMENTS_DIR = DATA_DIR / "documents"
DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)

# Load environment variables (.env in backend or root project dir)
load_dotenv(dotenv_path=BACKEND_DIR / ".env")
load_dotenv(dotenv_path=ROOT_DIR / ".env")
load_dotenv()

app = FastAPI(title="Visualizer API")

def get_analytics_attr(analytics, attr, default=None):
    if isinstance(analytics, dict):
        return analytics.get(attr, default)
    return getattr(analytics, attr, default)

def set_analytics_attr(analytics, attr, value):
    if isinstance(analytics, dict):
        analytics[attr] = value
    else:
        setattr(analytics, attr, value)

# Allow React frontend to communicate with backend dynamically from ALLOWED_ORIGINS env var
raw_origins = os.getenv("ALLOWED_ORIGINS")
allowed_origins = raw_origins.split(",") if raw_origins else DEFAULT_ALLOWED_ORIGINS

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/upload", response_model=UploadResponse)
async def upload_file(file: UploadFile = File(...)):
    start_time = time.perf_counter()
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
        
    filename = file.filename.lower()
    
    # File size check & async bytes extraction
    file_bytes = await file.read()
    file_size = len(file_bytes)
    
    if file_size > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=413, detail="File too large. Maximum allowed size is 16MB.")

    # Format validation check
    supported_exts = [".xlsx", ".csv", ".pdf", ".docx", ".doc", ".txt", ".md", ".rtf", ".xls"]
    if not any(filename.endswith(ext) for ext in supported_exts):
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type. Allowed formats: .xlsx, .csv, .pdf, .docx, .doc, .txt, .xls"
        )

    # SHA-256 hash & deduplicated storage filename
    import hashlib
    file_hash = hashlib.sha256(file_bytes).hexdigest()
    sanitized_name = os.path.basename(file.filename)
    unique_name = f"{file_hash[:10]}_{sanitized_name}"
    
    try:
        file_path = DOCUMENTS_DIR / unique_name
        with open(file_path, "wb") as f:
            f.write(file_bytes)
    except Exception as save_err:
        logger.warning(f"Could not save file '{file.filename}' to disk: {save_err}")

    # Delegate document execution to DocumentPipelineService
    try:
        from services.pipeline_service import get_pipeline_service
        pipeline_service = get_pipeline_service()
        response_payload = await asyncio.to_thread(pipeline_service.process_document, file_bytes, file.filename)
        response_payload.processing_time = round(time.perf_counter() - start_time, 2)
        return response_payload
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Pipeline error processing '{file.filename}': {e}")
        raise HTTPException(status_code=422, detail=f"Could not parse file. Error: {str(e)}")


@app.get("/api/health")
def health_check():
    return {"status": "ok", "nvidia_api": "configured"}

@app.get("/api/documents/{file_name}/metrics")
def get_document_metrics_api(file_name: str):
    from engine.db import get_metrics_by_file
    safe_name = os.path.basename(file_name)
    metrics = get_metrics_by_file(safe_name)
    if not metrics:
        raise HTTPException(status_code=404, detail="No metrics found for this document")
    return metrics

@app.get("/api/documents/{file_name}/pdf")
def get_document_pdf_api(file_name: str):
    from fastapi.responses import FileResponse
    safe_name = os.path.basename(file_name)
    file_path = DOCUMENTS_DIR / safe_name
    if not file_path.exists():
        matching_files = list(DOCUMENTS_DIR.glob(f"*_{safe_name}"))
        if matching_files:
            file_path = matching_files[-1]
        else:
            raise HTTPException(status_code=404, detail="Source PDF file not found on disk")
    return FileResponse(file_path, media_type="application/pdf", filename=safe_name)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=DEFAULT_HOST, port=DEFAULT_PORT, reload=True)

