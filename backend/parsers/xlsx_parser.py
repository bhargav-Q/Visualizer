import io
import openpyxl
from fastapi import UploadFile

def parse_xlsx(file: UploadFile):
    """
    Reads an uploaded .xlsx file using pure Python (openpyxl) and returns 
    raw column names and row data.
    """
    contents = file.file.read()
    file.file.seek(0)
    
    # Load workbook in read-only and data-only mode for performance and formulas
    wb = openpyxl.load_workbook(io.BytesIO(contents), data_only=True, read_only=True)
    sheet = wb.active
    
    # Extract headers
    rows_iter = sheet.iter_rows(values_only=True)
    try:
        headers = next(rows_iter)
    except StopIteration:
        return {"headers": [], "rows": []}
    
    # Clean headers
    headers = [str(h) if h is not None else f"Column_{i}" for i, h in enumerate(headers)]
    
    # Extract data rows
    data_rows = []
    for row in rows_iter:
        # Check if row is completely empty
        if all(cell is None for cell in row):
            continue
        data_rows.append(list(row))
        
    wb.close()
    
    return {
        "headers": headers,
        "rows": data_rows
    }
