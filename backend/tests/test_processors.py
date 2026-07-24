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
    
    mocker.patch("engine.vision_client.is_vision_api_disabled", return_value=False)
    mocker.patch("processors.text_processor.is_vision_api_disabled", return_value=False)
    mocker.patch("processors.text_processor.api_key", "test-key")
    
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


def test_resource_manager_worker_pool():
    """Test resource manager CPU-bounded worker pool calculation and list chunking."""
    from processors.resource_manager import get_resource_stats, chunk_list, get_global_executor
    import os

    stats = get_resource_stats()
    expected_cores = os.cpu_count() or 4
    expected_workers = max(1, expected_cores - 1)

    assert stats["total_cores"] == expected_cores
    assert stats["max_workers"] == expected_workers

    # Test chunking helper
    items = list(range(12))
    chunks = list(chunk_list(items, chunk_size=5))
    assert len(chunks) == 3
    assert chunks[0] == [0, 1, 2, 3, 4]
    assert chunks[1] == [5, 6, 7, 8, 9]
    assert chunks[2] == [10, 11]

    # Test global executor
    executor = get_global_executor()
    assert executor is not None


def test_extract_page_with_nemotron_sectioned(mocker):
    from processors.ocr_processor import extract_page_with_nemotron_sectioned
    mock_page = MagicMock()
    mock_page.rect = MagicMock(y0=0, y1=100, x0=0, x1=100)
    mock_pix = MagicMock()
    mock_pix.tobytes.return_value = b"somebytes"
    mock_page.get_pixmap.return_value = mock_pix
    
    mock_extract = mocker.patch("processors.ocr_processor.extract_tables_with_nemotron_ocr")
    mock_extract.return_value = {
        "data": [{
            "text_detections": [
                {"text_prediction": {"text": "hello"}},
                {"text_prediction": {"text": "world"}}
            ]
        }]
    }
    
    res = extract_page_with_nemotron_sectioned(mock_page)
    assert res == ["hello", "world"]


def test_extract_page_with_nemotron_sectioned_fallback(mocker):
    from processors.ocr_processor import extract_page_with_nemotron_sectioned
    mock_page = MagicMock()
    mock_page.rect = MagicMock(y0=0, y1=100, x0=0, x1=100)
    mock_pix = MagicMock()
    mock_pix.tobytes.return_value = b"somebytes"
    mock_page.get_pixmap.return_value = mock_pix
    
    # Force the main call to fail
    mock_extract = mocker.patch("processors.ocr_processor.extract_tables_with_nemotron_ocr")
    mock_extract.return_value = None
    
    # Mock get_ocr_engine to return None (no local OCR available) to test falling back through to Vision LLM
    mock_get_ocr = mocker.patch("parsers.pdf_parser.get_ocr_engine")
    mock_get_ocr.return_value = None
    
    # Mock Vision LLM
    mock_vision = mocker.patch("engine.vision_client.extract_analytics_with_vision")
    mock_analytics = MagicMock()
    mock_analytics.summary = "Summary text"
    mock_analytics.metrics = [MagicMock(context_snippet="Metric snippet")]
    mock_analytics.key_value_pairs = [MagicMock(context_snippet="KV snippet")]
    mock_vision.return_value = mock_analytics
    
    res = extract_page_with_nemotron_sectioned(mock_page)
    assert res == ["Summary text", "Metric snippet", "KV snippet"]




