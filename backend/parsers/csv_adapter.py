from typing import List
from fastapi import UploadFile
import io

from parsers.base import BaseParser
from contracts.document import DocumentContent, TableData
from parsers.csv_parser import parse_csv

class CSVParser(BaseParser):
    """Adapter wrapping csv_parser into the BaseParser contract."""
    
    @property
    def supported_extensions(self) -> List[str]:
        return [".csv"]

    @property
    def supported_mimes(self) -> List[str]:
        return ["text/csv", "application/csv"]

    def parse(self, file_bytes: bytes, filename: str) -> DocumentContent:
        upload_file = UploadFile(filename=filename, file=io.BytesIO(file_bytes))
        raw_res = parse_csv(upload_file)
        
        headers = raw_res.get("headers", [])
        rows = raw_res.get("rows", [])
        
        table = TableData(
            table_title=filename,
            headers=headers,
            rows=rows,
            page_number=1
        )
        
        return DocumentContent(
            raw_text="",
            tables=[table],
            metadata={"row_count": len(rows), "col_count": len(headers)},
            file_bytes=file_bytes
        )
