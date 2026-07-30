import pytest
import io
import pandas as pd
from services.tabular_service import process_tabular_file

def test_process_tabular_csv_bytes():
    csv_data = "Quarter,Revenue,Profit\nQ1,100,20\nQ2,150,35\nQ3,200,50"
    file_bytes = csv_data.encode("utf-8")
    
    result = process_tabular_file(file_bytes=file_bytes, filename="test_finance.csv")
    assert result["status"] == "success"
    assert result["tabular"]["total_rows"] == 3
    assert len(result["tabular"]["columns"]) == 3
    assert "data_preview" in result["tabular"]
    assert "markdown_table" in result["tabular"]
    assert "Quarter" in result["raw_markdown"]
    assert "Revenue" in result["raw_markdown"]

def test_process_tabular_invalid_extension():
    with pytest.raises(ValueError):
        process_tabular_file(file_bytes=b"dummy", filename="test.pdf")
