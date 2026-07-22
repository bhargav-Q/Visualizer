import pytest
import sys
from unittest.mock import MagicMock

# Import processors directly
from processors.text_processor import process_text
from processors.tabular_processor import process_tabular_data

def test_text_processor_success(mocker):
    """Test text processor successfully parses OpenAI API response without hitting the real API."""
    
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content='{"summary": "Test summary.", "keywords": [{"word": "test", "score": 0.99}]}'))
    ]
    
    # Mock the OpenAI client creation
    mock_openai = mocker.patch("processors.text_processor.OpenAI")
    mock_client_instance = mock_openai.return_value
    mock_client_instance.chat.completions.create.return_value = mock_response

    result = process_text("This is a test document.", page_count=1, paragraph_count=1)
    
    assert result.summary == "Test summary."
    assert len(result.keywords) == 1
    assert result.keywords[0].word == "test"
    assert result.keywords[0].score == 0.99
    assert result.word_count == 5

def test_tabular_processor_pure_python():
    """Test tabular processor with pure python dict."""
    
    mock_raw_data = {
        "headers": ["A", "B"],
        "rows": [
            [1, "test1"],
            [2, "test1"],
            [3, "test2"],
            [4, "test2"],
            [5, "test2"]
        ]
    }

    result = process_tabular_data(mock_raw_data)
    
    assert result.row_count == 5
    assert result.col_count == 2
    assert len(result.columns) == 2
    assert result.columns[0].name == "A"
    assert "A" in result.numeric_summary
    assert result.numeric_summary["A"].mean == 3.0
    assert "B" in result.categorical_summary
    assert result.categorical_summary["B"].unique == 2


def test_tabular_processor_smart_charts():
    """Test that tabular processor creates appropriate bar and line charts and skips high cardinality columns."""
    from datetime import datetime

    headers = ["TxnDate", "Debit", "Dept", "GLID"]
    rows = []
    # Create 22 rows to exceed the categorical threshold of 20 for GLID
    for i in range(22):
        date_val = datetime(2025, 1 + (i % 2), 1 + i)
        debit_val = float(100 + i * 10)
        dept_val = "HR" if i % 2 == 0 else "IT"
        glid_val = f"GL{i:03d}"  # Unique GLID for each row (22 unique values)
        rows.append([date_val, debit_val, dept_val, glid_val])

    mock_raw_data = {
        "headers": headers,
        "rows": rows
    }

    result = process_tabular_data(mock_raw_data)

    # 1. Assert line chart is generated for TxnDate
    line_charts = [c for c in result.charts if c.type == "line"]
    assert len(line_charts) > 0
    assert line_charts[0].x_key == "TxnDate"
    assert line_charts[0].y_key == "Debit"

    # 2. Assert bar chart is generated for Dept (cardinality 2)
    bar_charts = [c for c in result.charts if c.type == "bar"]
    assert len(bar_charts) > 0
    assert any(c.x_key == "Dept" for c in bar_charts)

    # 3. Assert NO chart is generated for GLID (since its cardinality is 22, which is > 20)
    assert not any(c.x_key == "GLID" for c in result.charts)


def test_csv_parser():
    from parsers.csv_parser import parse_csv
    from fastapi import UploadFile
    from io import BytesIO
    from datetime import datetime

    file_content = b"Date,Val,Category\n2025-01-01,10.5,Sales\n2025-01-02,20.0,Marketing\n"
    mock_file = UploadFile(filename="test.csv", file=BytesIO(file_content))

    result = parse_csv(mock_file)
    assert result["headers"] == ["Date", "Val", "Category"]
    assert len(result["rows"]) == 2
    assert isinstance(result["rows"][0][0], datetime)
    assert result["rows"][0][1] == 10.5
    assert result["rows"][0][2] == "Sales"


def test_parse_tsv_grid_dynamic_n_columns():
    """Test deterministic TSV grid parsing for dynamic N columns (e.g. 8+ columns)."""
    from processors.ocr_processor import parse_tsv_grid

    tsv_data = "Col1\tCol2\tCol3\tCol4\tCol5\tCol6\tCol7\tCol8\nVal1\tVal2\t100\t200\t$50.50\tSales\t2025-01-01\tUS\n"
    res = parse_tsv_grid(tsv_data)

    assert res is not None
    assert len(res["headers"]) == 8
    assert res["headers"] == ["Col1", "Col2", "Col3", "Col4", "Col5", "Col6", "Col7", "Col8"]
    assert len(res["rows"]) == 1
    assert res["rows"][0][4] == 50.5  # Currency stripped to numeric


def test_nemotron_ocr_v2_endpoint_mock(mocker):
    """Test Nemotron OCR v2 API handler with mocked 200 response."""
    from processors.ocr_processor import extract_tables_with_nemotron_ocr

    mock_post = mocker.patch("requests.post")
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {"detected_elements": ["Table 1"]}

    res = extract_tables_with_nemotron_ocr(b"fake_image_bytes")
    assert res == {"detected_elements": ["Table 1"]}


