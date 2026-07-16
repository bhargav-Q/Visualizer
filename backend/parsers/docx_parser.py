import docx
from fastapi import UploadFile
import io

def parse_docx(file: UploadFile) -> dict:
    """
    Reads an uploaded .docx file and extracts text and metadata.
    Returns a dictionary with 'text' and 'paragraph_count'.
    """
    contents = file.file.read()
    file.file.seek(0)
    
    # Use io.BytesIO to process in-memory
    doc = docx.Document(io.BytesIO(contents))
    
    full_text = []
    paragraph_count = 0
    
    for para in doc.paragraphs:
        # Only count non-empty paragraphs for stats
        if para.text.strip():
            full_text.append(para.text)
            paragraph_count += 1
            
    return {
        "text": "\n".join(full_text),
        "paragraph_count": paragraph_count
    }
