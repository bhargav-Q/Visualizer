from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import logging

from models.schemas import UploadResponse
from parsers.xlsx_parser import parse_xlsx
from processors.tabular_processor import process_tabular_data

# Suppress harmless pdfminer warnings about fonts
logging.getLogger("pdfminer").setLevel(logging.ERROR)

# Load environment variables (NVIDIA_API_KEY)
load_dotenv()

app = FastAPI(title="Visualizer API")

# Allow React frontend to communicate with backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/upload", response_model=UploadResponse)
async def upload_file(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
        
    filename = file.filename.lower()
    
    # File size check (15MB)
    file.file.seek(0, 2) # seek to end
    file_size = file.file.tell()
    file.file.seek(0)    # reset to start
    
    if file_size > 15 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large. Maximum allowed size is 15MB.")
    
    if filename.endswith(".xlsx"):
        try:
            raw_data = parse_xlsx(file)
            tabular_data = process_tabular_data(raw_data)
            return UploadResponse(
                file_name=file.filename,
                file_type="xlsx",
                data_category="tabular",
                tabular=tabular_data,
                text=None
            )
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"Could not parse file. It may be corrupted. Error: {str(e)}")
            
    elif filename.endswith(".csv"):
        try:
            from parsers.csv_parser import parse_csv
            raw_data = parse_csv(file)
            tabular_data = process_tabular_data(raw_data)
            return UploadResponse(
                file_name=file.filename,
                file_type="csv",
                data_category="tabular",
                tabular=tabular_data,
                text=None
            )
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"Could not parse file. It may be corrupted. Error: {str(e)}")
            
    elif filename.endswith(".pdf"):
        try:
            import concurrent.futures
            from parsers.pdf_parser import parse_pdf
            from processors.text_processor import process_text
            from processors.ocr_processor import extract_tables_from_pdf
            
            # Read file bytes once for both text parsing and table extraction
            file_bytes = file.file.read()
            file.file.seek(0)
            
            parsed_data = parse_pdf(file)

            # Run Text Summary and Table Extraction concurrently in parallel
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                future_text = executor.submit(
                    process_text,
                    raw_text=parsed_data["text"],
                    page_count=parsed_data["page_count"],
                    paragraph_count=None
                )
                future_table = executor.submit(extract_tables_from_pdf, file_bytes)

                text_data = future_text.result()
                raw_table = future_table.result()

            tabular_data = None
            data_category = "text"
            if raw_table and raw_table.get("rows"):
                tabular_data = process_tabular_data(raw_table)
                data_category = "mixed"

            return UploadResponse(
                file_name=file.filename,
                file_type="pdf",
                data_category=data_category,
                tabular=tabular_data,
                text=text_data
            )
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"Could not parse file. It may be corrupted. Error: {str(e)}")

    elif filename.endswith(".docx"):
        try:
            from parsers.docx_parser import parse_docx
            from processors.text_processor import process_text
            
            parsed_data = parse_docx(file)
            text_data = process_text(
                raw_text=parsed_data["text"],
                page_count=None,
                paragraph_count=parsed_data["paragraph_count"]
            )
            return UploadResponse(
                file_name=file.filename,
                file_type="docx",
                data_category="text",
                tabular=None,
                text=text_data
            )
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"Could not parse file. It may be corrupted. Error: {str(e)}")

    else:
        raise HTTPException(status_code=400, detail="Unsupported file type. Allowed: .xlsx, .pdf, .docx, .csv")

@app.get("/api/health")
def health_check():
    return {"status": "ok", "nvidia_api": "configured"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
