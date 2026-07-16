import pandas as pd
from fastapi import UploadFile
import io

def parse_xlsx(file: UploadFile) -> pd.DataFrame:
    """
    Reads an uploaded .xlsx file and returns a Pandas DataFrame.
    """
    contents = file.file.read()
    file.file.seek(0)  # Reset pointer in case it needs to be read again
    
    # Use io.BytesIO to treat the bytes as a file for pandas
    df = pd.read_excel(io.BytesIO(contents))
    return df
