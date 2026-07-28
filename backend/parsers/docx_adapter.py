from typing import List
from fastapi import UploadFile
import io

from parsers.base import BaseParser
from contracts.document import DocumentContent
from parsers.docx_parser import parse_docx

class DOCXParser(BaseParser):
    """Adapter wrapping docx_parser into the BaseParser contract."""
    
    @property
    def supported_extensions(self) -> List[str]:
        return [".docx", ".doc"]

    @property
    def supported_mimes(self) -> List[str]:
        return [
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/msword"
        ]

    def parse(self, file_bytes: bytes, filename: str) -> DocumentContent:
        upload_file = UploadFile(filename=filename, file=io.BytesIO(file_bytes))
        raw_res = parse_docx(upload_file)
        
        text = raw_res.get("text", "")
        structured_tsv = raw_res.get("structured_tsv", "")
        paragraph_count = raw_res.get("paragraph_count", 0)
        
        return DocumentContent(
            raw_text=text,
            structured_tsv=structured_tsv,
            paragraph_count=paragraph_count,
            page_count=1,
            metadata={"paragraph_count": paragraph_count},
            file_bytes=file_bytes
        )
