from typing import List
from fastapi import UploadFile
import io

from parsers.base import BaseParser
from contracts.document import DocumentContent
from parsers.txt_parser import parse_txt

class TXTParser(BaseParser):
    """Adapter wrapping txt_parser into the BaseParser contract."""
    
    @property
    def supported_extensions(self) -> List[str]:
        return [".txt", ".md", ".rtf"]

    @property
    def supported_mimes(self) -> List[str]:
        return ["text/plain", "text/markdown", "application/rtf"]

    def parse(self, file_bytes: bytes, filename: str) -> DocumentContent:
        upload_file = UploadFile(filename=filename, file=io.BytesIO(file_bytes))
        raw_res = parse_txt(upload_file)
        
        text = raw_res.get("text", "")
        paragraph_count = raw_res.get("paragraph_count", 0)
        
        return DocumentContent(
            raw_text=text,
            tables=[],
            metadata={"word_count": len(text.split()) if text else 0},
            paragraph_count=paragraph_count,
            page_count=1,
            file_bytes=file_bytes
        )
