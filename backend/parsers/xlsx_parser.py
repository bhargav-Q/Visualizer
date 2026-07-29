import io
import logging
import openpyxl
from fastapi import UploadFile

logger = logging.getLogger(__name__)

def parse_xlsx(file: UploadFile):
    """
    Reads an uploaded .xlsx file using openpyxl and returns data for
    ALL worksheets in the workbook.

    Returns:
        dict with keys:
            - headers: list[str]       (from first non-empty sheet, backward compat)
            - rows: list[list]         (from first non-empty sheet, backward compat)
            - sheets: list[dict]       (all worksheets with sheet_name, headers, rows)
    """
    file.file.seek(0)
    contents = file.file.read()
    file.file.seek(0)

    wb = openpyxl.load_workbook(io.BytesIO(contents), data_only=True, read_only=True)

    sheets = []
    primary_headers = []
    primary_rows = []

    for sheet_name in wb.sheetnames:
        sheet = wb[sheet_name]
        rows_iter = sheet.iter_rows(values_only=True)

        # Extract headers
        try:
            raw_headers = next(rows_iter)
        except StopIteration:
            # Empty sheet — skip
            continue

        headers = [str(h) if h is not None else f"Column_{i}" for i, h in enumerate(raw_headers)]

        # Extract data rows
        data_rows = []
        for row in rows_iter:
            if all(cell is None for cell in row):
                continue
            data_rows.append(list(row))

        # Skip sheets with no data rows
        if not data_rows:
            continue

        sheet_entry = {
            "sheet_name": sheet_name,
            "headers": headers,
            "rows": data_rows,
            "row_count": len(data_rows),
            "col_count": len(headers)
        }
        sheets.append(sheet_entry)

        # First non-empty sheet becomes the primary (backward compatibility)
        if not primary_headers:
            primary_headers = headers
            primary_rows = data_rows

    wb.close()

    return {
        "headers": primary_headers,
        "rows": primary_rows,
        "sheets": sheets
    }
