from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import time
import logging

from models.schemas import UploadResponse
from parsers.xlsx_parser import parse_xlsx
from parsers.pdf_parser import parse_pdf
from parsers.docx_parser import parse_docx
from parsers.txt_parser import parse_txt
from parsers.image_parser import parse_image
from processors.tabular_processor import process_tabular_data
from processors.text_processor import process_text
from processors.ocr_processor import extract_tables_from_text, parse_tsv_grid

# Suppress harmless pdfminer warnings about fonts
logging.getLogger("pdfminer").setLevel(logging.ERROR)

logger = logging.getLogger(__name__)

from pathlib import Path
import os
BACKEND_DIR = Path(__file__).resolve().parent
ROOT_DIR = BACKEND_DIR.parent
DATA_DIR = ROOT_DIR / "data"
DOCUMENTS_DIR = DATA_DIR / "documents"
DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)

# Load environment variables (.env in backend or root project dir)
load_dotenv(dotenv_path=BACKEND_DIR / ".env")
load_dotenv(dotenv_path=ROOT_DIR / ".env")
load_dotenv()

app = FastAPI(title="Visualizer API")

# Allow React frontend to communicate with backend dynamically from ALLOWED_ORIGINS env var
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/upload", response_model=UploadResponse)
def upload_file(file: UploadFile = File(...)):
    start_time = time.perf_counter()
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
        
    filename = file.filename.lower()
    
    # File size check (16MB)
    file.file.seek(0, 2) # seek to end
    file_size = file.file.tell()
    file.file.seek(0)    # reset to start
    
    if file_size > 16 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large. Maximum allowed size is 16MB.")
        
    try:
        file_bytes = file.file.read()
        file.file.seek(0)
    except Exception:
        file_bytes = b""

    # SHA-256 hash & deduplicated storage filename
    import hashlib
    from engine.db import get_cached_analytics, save_cached_analytics
    file_hash = hashlib.sha256(file_bytes).hexdigest()
    
    sanitized_name = os.path.basename(file.filename)
    unique_name = f"{file_hash[:10]}_{sanitized_name}"
    
    try:
        file_path = DOCUMENTS_DIR / unique_name
        with open(file_path, "wb") as f:
            f.write(file_bytes)
        file.file.seek(0)
    except Exception as save_err:
        logger.warning(f"Could not save file '{file.filename}' to disk: {save_err}")

    # SHA-256 caching logic with stale schema recovery
    try:
        cached_payload = get_cached_analytics(file_hash)
        if cached_payload:
            logger.info(f"[PROFILER] Cache HIT for file '{file.filename}' (hash: {file_hash})")
            cached_payload["file_name"] = file.filename
            cached_payload["processing_time"] = round(time.perf_counter() - start_time, 4)
            return UploadResponse(**cached_payload)
    except Exception as cache_err:
        logger.warning(f"[WARNING] Stale cache schema detected. Re-parsing document... Details: {cache_err}")

    response_payload = None
    
    if filename.endswith(".xlsx"):
        try:
            t0 = time.perf_counter()
            raw_data = parse_xlsx(file)
            tabular_data = process_tabular_data(raw_data)
            logger.info(f"[PROFILER] XLSX Parsing & Processing: {time.perf_counter() - t0:.4f}s")
            response_payload = UploadResponse(
                file_name=file.filename,
                file_type="xlsx",
                data_category="tabular",
                tabular=tabular_data,
                text=None,
                processing_time=0.0
            )
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"Could not parse file. It may be corrupted. Error: {str(e)}")
            
    elif filename.endswith(".csv"):
        try:
            t0 = time.perf_counter()
            from parsers.csv_parser import parse_csv
            raw_data = parse_csv(file)
            tabular_data = process_tabular_data(raw_data)
            logger.info(f"[PROFILER] CSV Parsing & Processing: {time.perf_counter() - t0:.4f}s")
            response_payload = UploadResponse(
                file_name=file.filename,
                file_type="csv",
                data_category="tabular",
                tabular=tabular_data,
                text=None,
                processing_time=0.0
            )
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"Could not parse file. It may be corrupted. Error: {str(e)}")
            
    elif filename.endswith(".pdf"):
        try:
            import concurrent.futures
            
            t0 = time.perf_counter()
            parsed_data = parse_pdf(file)
            logger.info(f"[PROFILER] PDF Text & Spatial Grid Parsing: {time.perf_counter() - t0:.4f}s")

            # Run Text Summary, Table Extraction, and Unstructured Document Extraction concurrently
            from processors.resource_manager import get_global_executor
            from engine.document_extractor import process_unstructured_document
            executor = get_global_executor()
            
            t1 = time.perf_counter()
            future_text = executor.submit(
                process_text,
                raw_text=parsed_data["text"],
                page_count=parsed_data["page_count"],
                paragraph_count=None
            )
            table_input_text = parsed_data.get("structured_tsv") or parsed_data["text"]
            future_table = executor.submit(extract_tables_from_text, table_input_text)
            future_analytics = executor.submit(process_unstructured_document, file)

            text_data = future_text.result()
            try:
                raw_table = future_table.result()
            except Exception as table_err:
                logger.warning(f"DeepSeek table extraction failed, falling back to TSV backstop: {table_err}")
                raw_table = None

            try:
                analytics_result = future_analytics.result()
                analytics_data = analytics_result.get("analytics")
            except Exception as analytics_err:
                logger.warning(f"Analytics extraction failed: {analytics_err}")
                analytics_data = None
            
            logger.info(f"[PROFILER] Parallel PDF AI Extractor Calls: {time.perf_counter() - t1:.4f}s")

            # Deterministic TSV Table Fallback Backstop
            if not raw_table or not raw_table.get("rows"):
                raw_table = parse_tsv_grid(parsed_data.get("structured_tsv") or parsed_data["text"])

            tabular_data = None
            data_category = "text"
            if raw_table and raw_table.get("rows"):
                tabular_data = process_tabular_data(raw_table)
                data_category = "mixed"

            response_payload = UploadResponse(
                file_name=file.filename,
                file_type="pdf",
                data_category=data_category,
                tabular=tabular_data,
                text=text_data,
                analytics=analytics_data,
                processing_time=0.0
            )
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"Could not parse file. It may be corrupted. Error: {str(e)}")

    elif filename.endswith((".docx", ".doc")):
        try:
            t0 = time.perf_counter()
            parsed_data = parse_docx(file)
            raw_text = parsed_data.get("text", "")
            paragraph_count = parsed_data.get("paragraph_count")
            logger.info(f"[PROFILER] Word Doc Native Parsing: {time.perf_counter() - t0:.4f}s")

            from processors.resource_manager import get_global_executor
            from engine.document_extractor import process_unstructured_document
            executor = get_global_executor()
            
            t1 = time.perf_counter()
            future_text = executor.submit(
                process_text,
                raw_text=raw_text,
                page_count=None,
                paragraph_count=paragraph_count
            )
            table_input_text = parsed_data.get("structured_tsv") or raw_text
            future_table = executor.submit(extract_tables_from_text, table_input_text)
            future_analytics = executor.submit(process_unstructured_document, file)

            text_data = future_text.result()
            try:
                raw_table = future_table.result()
            except Exception as table_err:
                logger.warning(f"DeepSeek table extraction failed for DOCX, falling back to TSV backstop: {table_err}")
                raw_table = None

            try:
                analytics_result = future_analytics.result()
                analytics_data = analytics_result.get("analytics")
            except Exception as analytics_err:
                logger.warning(f"Analytics extraction failed for DOCX: {analytics_err}")
                analytics_data = None

            logger.info(f"[PROFILER] Parallel DOCX AI Extractor Calls: {time.perf_counter() - t1:.4f}s")

            # DOCX TSV Fallback Backstop (matching PDF pathway)
            if not raw_table or not raw_table.get("rows"):
                raw_table = parse_tsv_grid(parsed_data.get("structured_tsv") or raw_text)

            tabular_data = None
            data_category = "text"
            if raw_table and raw_table.get("rows"):
                tabular_data = process_tabular_data(raw_table)
                data_category = "mixed"

            file_ext = "docx" if filename.endswith(".docx") else "doc"
            response_payload = UploadResponse(
                file_name=file.filename,
                file_type=file_ext,
                data_category=data_category,
                tabular=tabular_data,
                text=text_data,
                analytics=analytics_data,
                processing_time=0.0
            )
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"Could not parse file. It may be corrupted. Error: {str(e)}")

    elif filename.endswith(".txt"):
        try:
            t0 = time.perf_counter()
            parsed_data = parse_txt(file)
            raw_text = parsed_data.get("text", "")
            paragraph_count = parsed_data.get("paragraph_count")
            logger.info(f"[PROFILER] TXT File Parsing: {time.perf_counter() - t0:.4f}s")

            from processors.resource_manager import get_global_executor
            from engine.document_extractor import process_unstructured_document
            executor = get_global_executor()
            
            t1 = time.perf_counter()
            future_text = executor.submit(
                process_text,
                raw_text=raw_text,
                page_count=None,
                paragraph_count=paragraph_count
            )
            future_table = executor.submit(extract_tables_from_text, raw_text)
            future_analytics = executor.submit(process_unstructured_document, file)

            text_data = future_text.result()
            try:
                raw_table = future_table.result()
            except Exception as table_err:
                logger.warning(f"DeepSeek table extraction failed for TXT file, falling back to TSV backstop: {table_err}")
                raw_table = None

            try:
                analytics_result = future_analytics.result()
                analytics_data = analytics_result.get("analytics")
            except Exception as analytics_err:
                logger.warning(f"Analytics extraction failed for TXT: {analytics_err}")
                analytics_data = None

            logger.info(f"[PROFILER] Parallel TXT AI Extractor Calls: {time.perf_counter() - t1:.4f}s")

            tabular_data = None
            data_category = "text"
            if raw_table and raw_table.get("rows"):
                tabular_data = process_tabular_data(raw_table)
                data_category = "mixed"

            file_ext = filename.split(".")[-1].lower()
            response_payload = UploadResponse(
                file_name=file.filename,
                file_type=file_ext,
                data_category=data_category,
                tabular=tabular_data,
                text=text_data,
                analytics=analytics_data,
                processing_time=0.0
            )
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"Could not parse file. Error: {str(e)}")

    else:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type. Allowed formats: .xlsx, .csv, .pdf, .docx, .doc, .txt"
        )

    # Cache response payload and populate processing time dynamically on cache miss
    if response_payload:
        try:
            cache_dict = response_payload.model_dump()
            cache_dict.pop("processing_time", None)
            save_cached_analytics(file_hash, file.filename, cache_dict)
        except Exception as cache_err:
            logger.warning(f"Failed to cache response in upload endpoint: {cache_err}")
        
        response_payload.processing_time = round(time.perf_counter() - start_time, 2)
        return response_payload

    else:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type. Allowed formats: .xlsx, .csv, .pdf, .docx, .doc, .txt"
        )


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
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
