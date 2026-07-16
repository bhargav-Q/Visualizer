from fastapi import UploadFile
import io
import pypdf

def parse_pdf(file: UploadFile) -> dict:
    """
    Reads an uploaded .pdf file and extracts text and metadata
    using pure Python (pypdf) to avoid AppLocker DLL blocks.
    """
    contents = file.file.read()
    file.file.seek(0)
    
    full_text = []
    
    # Process in-memory
    reader = pypdf.PdfReader(io.BytesIO(contents))
    page_count = len(reader.pages)
    
    for page in reader.pages:
        extracted = page.extract_text()
        if extracted:
            full_text.append(extracted)
                
    return {
        "text": "\n".join(full_text),
        "page_count": page_count
    }
