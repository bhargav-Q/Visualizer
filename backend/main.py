from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from models.schemas import UploadResponse
from parsers.xlsx_parser import parse_xlsx
from processors.tabular_processor import process_dataframe

# Load environment variables (NVIDIA_API_KEY)
load_dotenv()

app = FastAPI(title="Visualizer API")

# Allow React frontend to communicate with backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/upload", response_model=UploadResponse)
async def upload_file(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
        
    filename = file.filename.lower()
    
    # Optional: File size check (15MB) - typically handled by web server, but we can check here.
    
    if filename.endswith(".xlsx"):
        try:
            df = parse_xlsx(file)
            tabular_data = process_dataframe(df)
            return UploadResponse(
                file_name=file.filename,
                file_type="xlsx",
                data_category="tabular",
                tabular=tabular_data,
                text=None
            )
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"Could not parse file. It may be corrupted. Error: {str(e)}")
            
    elif filename.endswith((".pdf", ".docx")):
        raise HTTPException(status_code=501, detail="Text processing is not implemented yet (Phase 2)")
    
    else:
        raise HTTPException(status_code=400, detail="Unsupported file type. Allowed: .xlsx, .pdf, .docx")

@app.get("/api/health")
def health_check():
    return {"status": "ok", "nvidia_api": "configured"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
