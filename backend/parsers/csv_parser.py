import csv
import io
from fastapi import UploadFile
from datetime import datetime

DATE_FORMATS = [
    "%Y-%m-%d",
    "%Y-%m-%d %H:%M:%S",
    "%d-%m-%Y",
    "%m/%d/%Y",
    "%m/%d/%Y %H:%M",
]

def try_parse_value(val: str):
    val_clean = val.strip()
    if not val_clean:
        return None
        
    # 1. Try numeric parsing
    try:
        if '.' in val_clean:
            return float(val_clean)
        else:
            return int(val_clean)
    except ValueError:
        pass
        
    # 2. Try datetime parsing
    # First, try standard ISO / fromisoformat
    try:
        return datetime.fromisoformat(val_clean)
    except ValueError:
        pass
        
    # Try custom common formats
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(val_clean, fmt)
        except ValueError:
            pass
            
    return val_clean

def parse_csv(file: UploadFile) -> dict:
    """
    Reads an uploaded .csv file using pure Python and returns 
    raw column names and row data.
    """
    contents = file.file.read()
    file.file.seek(0)
    
    # Try decoding as UTF-8 (with BOM check), fallback to Latin-1
    try:
        decoded_content = contents.decode("utf-8-sig")
    except UnicodeDecodeError:
        decoded_content = contents.decode("latin-1")
        
    csv_file = io.StringIO(decoded_content)
    reader = csv.reader(csv_file)
    
    try:
        headers = next(reader)
    except StopIteration:
        return {"headers": [], "rows": []}
        
    # Clean headers
    headers = [str(h).strip() if h is not None else f"Column_{i}" for i, h in enumerate(headers)]
    
    data_rows = []
    for row in reader:
        # Check if row is completely empty
        if not row or all(cell == "" or cell is None for cell in row):
            continue
            
        parsed_row = [try_parse_value(cell) for cell in row]
        # Pad row to match number of headers if they are shorter
        if len(parsed_row) < len(headers):
            parsed_row.extend([None] * (len(headers) - len(parsed_row)))
        # Truncate row if it exceeds headers
        elif len(parsed_row) > len(headers):
            parsed_row = parsed_row[:len(headers)]
            
        data_rows.append(parsed_row)
        
    return {
        "headers": headers,
        "rows": data_rows
    }
