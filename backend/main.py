import time
import asyncio
import logging
import os
import uuid
import hashlib
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from dotenv import load_dotenv

from models.schemas import UploadResponse
from config import MAX_FILE_SIZE_BYTES, DEFAULT_ALLOWED_ORIGINS, BACKEND_DIR, ROOT_DIR, DATA_DIR, DEFAULT_HOST, DEFAULT_PORT
from logger import current_trace_id, get_visualizer_logger
from services.pipeline_service import get_pipeline_service
from engine.db import get_metrics_by_file

# Suppress pdfminer font warnings
logging.getLogger("pdfminer").setLevel(logging.ERROR)

logger = get_visualizer_logger("main")
DOCUMENTS_DIR = DATA_DIR / "documents"
DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)

# Load environment variables
load_dotenv(dotenv_path=BACKEND_DIR / ".env")
load_dotenv(dotenv_path=ROOT_DIR / ".env")
load_dotenv()

app = FastAPI(title="Visualizer API")

# Allow React frontend to communicate with backend
raw_origins = os.getenv("ALLOWED_ORIGINS")
allowed_origins = raw_origins.split(",") if raw_origins else DEFAULT_ALLOWED_ORIGINS

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def trace_id_middleware(request, call_next):
    trace_id = request.headers.get("X-Trace-ID") or str(uuid.uuid4())[:8]
    token = current_trace_id.set(trace_id)
    try:
        response = await call_next(request)
        response.headers["X-Trace-ID"] = trace_id
        return response
    finally:
        current_trace_id.reset(token)

@app.post("/api/upload")
@app.post("/api/v1/upload")
async def upload_file(file: UploadFile = File(...)):
    start_time = time.perf_counter()
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
        
    filename = file.filename.lower()
    file_bytes = await file.read()
    file_size = len(file_bytes)
    
    if file_size > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=413, detail="File too large. Maximum allowed size is 16MB.")

    supported_exts = [".xlsx", ".csv", ".pdf", ".docx"]
    if not any(filename.endswith(ext) for ext in supported_exts):
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type. Allowed formats: .xlsx, .csv, .pdf, .docx"
        )

    file_hash = hashlib.sha256(file_bytes).hexdigest()
    sanitized_name = os.path.basename(file.filename)
    unique_name = f"{file_hash[:10]}_{sanitized_name}"
    
    try:
        file_path = DOCUMENTS_DIR / unique_name
        with open(file_path, "wb") as f:
            f.write(file_bytes)
    except Exception as save_err:
        logger.warning(f"Could not save file '{file.filename}' to disk: {save_err}")

    try:
        from services.main_pipeline import run_file_to_dashboard_pipeline
        pipeline_result = await asyncio.to_thread(
            run_file_to_dashboard_pipeline,
            file_bytes=file_bytes,
            filename=file.filename
        )
        pipeline_result["processing_time"] = round(time.perf_counter() - start_time, 2)
        return pipeline_result
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Pipeline error processing '{file.filename}': {e}")
        raise HTTPException(status_code=422, detail=f"Could not parse file. Error: {str(e)}")

@app.post("/api/ocr/mistral")
async def mistral_ocr_direct_api(file: UploadFile = File(...)):
    """
    Direct endpoint for hitting official Mistral OCR API (`mistral-ocr-latest`) with PDF/Image form-data.
    Returns the complete layout-accurate extracted Markdown (.md) content directly.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
        
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Empty file buffer")

    try:
        from services.mistral_ocr_service import process_document_with_mistral_ocr
        base_name = os.path.splitext(os.path.basename(file.filename))[0]
        output_dir = DATA_DIR / "outputs"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_md_path = output_dir / f"{base_name}.md"
        
        res = await asyncio.to_thread(
            process_document_with_mistral_ocr,
            file_bytes=file_bytes,
            filename=file.filename,
            output_md_path=str(output_md_path)
        )
        
        md_text = res.get("markdown_text", "")
        return Response(
            content=md_text,
            media_type="text/markdown; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="{base_name}.md"'
            }
        )
    except Exception as exc:
        logger.error(f"Direct Mistral OCR API error for '{file.filename}': {exc}")
        raise HTTPException(status_code=500, detail=f"Mistral OCR processing error: {str(exc)}")

@app.get("/api/health")
def health_check():
    return {"status": "ok", "mistral_ocr": "active"}

@app.get("/api/documents/{file_name}/metrics")
def get_document_metrics_api(file_name: str):
    safe_name = os.path.basename(file_name)
    metrics = get_metrics_by_file(safe_name)
    if not metrics:
        raise HTTPException(status_code=404, detail="No metrics found for this document")
    return metrics

@app.get("/api/documents/{file_name}/pdf")
def get_document_pdf_api(file_name: str):
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
