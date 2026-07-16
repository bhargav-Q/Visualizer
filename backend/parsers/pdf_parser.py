import pdfplumber
from fastapi import UploadFile
import io

def parse_pdf(file: UploadFile) -> dict:
    """
    Reads an uploaded .pdf file and extracts text and metadata.
    Returns a dictionary with 'text' and 'page_count'.
    """
    contents = file.file.read()
    file.file.seek(0)
    
    full_text = []
    page_count = 0
    
    # Use io.BytesIO to process in-memory
    with pdfplumber.open(io.BytesIO(contents)) as pdf:
        page_count = len(pdf.pages)
        for page in pdf.pages:
            extracted = page.extract_text()
            if extracted:
                full_text.append(extracted)
                
    return {
        "text": "\n".join(full_text),
        "page_count": page_count
    }
