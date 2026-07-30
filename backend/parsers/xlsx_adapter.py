from typing import List
from fastapi import UploadFile
import io

from parsers.base import BaseParser
from contracts.document import DocumentContent, TableData
from parsers.xlsx_parser import parse_xlsx

class XLSXParser(BaseParser):
    """Adapter wrapping xlsx_parser into the BaseParser contract with multi-sheet support."""
    
    @property
    def supported_extensions(self) -> List[str]:
        return [".xlsx"]

    @property
    def supported_mimes(self) -> List[str]:
        return [
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/xlsx"
        ]

    def parse(self, file_bytes: bytes, filename: str) -> DocumentContent:
        upload_file = UploadFile(filename=filename, file=io.BytesIO(file_bytes))
        raw_res = parse_xlsx(upload_file)
        
        tables = []
        sheets_data = raw_res.get("sheets", [])
        
        if sheets_data:
            # Multi-sheet: create one TableData per worksheet
            for sheet in sheets_data:
                tables.append(TableData(
                    table_title=f"Sheet: {sheet['sheet_name']}",
                    headers=sheet["headers"],
                    rows=sheet["rows"],
                    page_number=1
                ))
        else:
            # Fallback: single sheet from legacy keys
            headers = raw_res.get("headers", [])
            rows = raw_res.get("rows", [])
            if headers or rows:
                tables.append(TableData(
                    table_title=filename,
                    headers=headers,
                    rows=rows,
                    page_number=1
                ))

        total_rows = sum(len(t.rows) for t in tables)
        total_cols = max((len(t.headers) for t in tables), default=0)

        return DocumentContent(
            raw_text="",
            tables=tables,
            metadata={
                "row_count": total_rows,
                "col_count": total_cols,
                "sheet_count": len(tables),
                "warnings": raw_res.get("warnings", [])
            },
            file_bytes=file_bytes
        )