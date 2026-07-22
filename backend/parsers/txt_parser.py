from fastapi import UploadFile
import re

def parse_txt(file: UploadFile) -> dict:
    """
    Reads an uploaded .txt, .md, or .rtf file and extracts text and metadata.
    """
    file.file.seek(0)
    raw_bytes = file.file.read()
    file.file.seek(0)


    # Try decoding UTF-8 first, fallback to latin-1
    try:
        text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        text = raw_bytes.decode("latin-1", errors="replace")

    filename = file.filename.lower() if file.filename else ""

    # Simple RTF tag stripping if file is RTF
    if filename.endswith(".rtf"):
        # Strip RTF control words and groups
        text = re.sub(r'{\\connection[^}]*}', '', text)
        text = re.sub(r'\\[a-z1-9]+\b\s?', '', text)
        text = re.sub(r'[{}]', '', text)
        text = text.strip()

    # Calculate paragraphs (separated by double newlines or single non-empty lines)
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]

    return {
        "text": text,
        "paragraph_count": len(paragraphs)
    }
