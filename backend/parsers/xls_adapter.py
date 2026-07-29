from typing import List
import io
import logging

from parsers.base import BaseParser
from contracts.document import DocumentContent, TableData

logger = logging.getLogger(__name__)

class XLSParser(BaseParser):
    """Adapter for legacy Excel binary files (.xls) with multi-sheet support and graceful fallback."""
    
    @property
    def supported_extensions(self) -> List[str]:
        return [".xls"]

    @property
    def supported_mimes(self) -> List[str]:
        return [
            "application/vnd.ms-excel",
            "application/msexcel"
        ]

    def parse(self, file_bytes: bytes, filename: str) -> DocumentContent:
        tables = []
        try:
            import xlrd
            wb = xlrd.open_workbook(file_contents=file_bytes)

            for sheet_idx in range(wb.nsheets):
                sheet = wb.sheet_by_index(sheet_idx)
                if sheet.nrows < 1:
                    continue

                headers = [str(cell) for cell in sheet.row_values(0)]
                rows = []
                for r in range(1, sheet.nrows):
                    rows.append(sheet.row_values(r))

                if not rows:
                    continue

                tables.append(TableData(
                    table_title=f"Sheet: {sheet.name}",
                    headers=headers,
                    rows=rows,
                    page_number=1
                ))

        except Exception as e:
            logger.warning(f"xlrd reading failed for legacy xls file '{filename}': {e}. Attempting basic text stream fallback.")
            try:
                text_content = file_bytes.decode("latin-1", errors="replace")
                lines = [l.strip() for l in text_content.split("\n") if "\t" in l]
                if lines:
                    headers = [c.strip() for c in lines[0].split("\t")]
                    rows = []
                    for l in lines[1:]:
                        rows.append([c.strip() for c in l.split("\t")])
                    if rows:
                        tables.append(TableData(
                            table_title=filename,
                            headers=headers,
                            rows=rows,
                            page_number=1
                        ))
            except Exception as txt_err:
                logger.error(f"Legacy XLS parsing fallback failed: {txt_err}")

        total_rows = sum(len(t.rows) for t in tables)
        total_cols = max((len(t.headers) for t in tables), default=0)

        return DocumentContent(
            raw_text="",
            tables=tables,
            metadata={
                "row_count": total_rows,
                "col_count": total_cols,
                "sheet_count": len(tables)
            },
            file_bytes=file_bytes
        )
