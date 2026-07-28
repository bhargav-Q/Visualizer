from typing import List
from fastapi import UploadFile
import io

from parsers.base import BaseParser
from contracts.document import DocumentContent
from parsers.pdf_parser import parse_pdf

class PDFParser(BaseParser):
    """Adapter wrapping pdf_parser into the BaseParser contract."""
    
    @property
    def supported_extensions(self) -> List[str]:
        return [".pdf"]

    @property
    def supported_mimes(self) -> List[str]:
        return ["application/pdf"]

    def parse(self, file_bytes: bytes, filename: str) -> DocumentContent:
        upload_file = UploadFile(filename=filename, file=io.BytesIO(file_bytes))
        raw_res = parse_pdf(upload_file)
        
        text = raw_res.get("text", "")
        structured_tsv = raw_res.get("structured_tsv", "")
        page_count = raw_res.get("page_count", 1)
        blocks_by_page = raw_res.get("blocks_by_page", {})
        tables = raw_res.get("tables", [])
        
        return DocumentContent(
            raw_text=text,
            structured_tsv=structured_tsv,
            tables=tables,
            page_count=page_count,
            blocks_by_page=blocks_by_page,
            metadata={"page_count": page_count},
            file_bytes=file_bytes
        )
