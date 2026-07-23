import pytest
from io import BytesIO

def test_upload_invalid_file_type(client):
    """Test that an unsupported file type (.exe) is rejected."""
    file_content = b"Some binary executable data"
    files = {"file": ("test.exe", file_content, "application/octet-stream")}
    response = client.post("/api/upload", files=files)
    
    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]

def test_upload_file_too_large(client, mocker):
    """Test that a >16MB file is rejected."""
    large_content = b"0" * (16 * 1024 * 1024 + 1)
    files = {"file": ("large.pdf", large_content, "application/pdf")}
    response = client.post("/api/upload", files=files)
    
    assert response.status_code == 413
    assert "File too large" in response.json()["detail"]

def test_upload_valid_pdf_endpoint(client, mocker):
    """Test uploading a valid PDF, mocking the internal parsers to avoid API calls."""
    from models.schemas import TextResult, KeywordItem
    
    mocker.patch("main.parse_pdf", return_value={"text": "Mocked PDF text", "page_count": 1, "structured_tsv": ""})
    mocker.patch("main.extract_tables_from_text", return_value=None)
    mocker.patch("main.parse_tsv_grid", return_value=None)
    mocker.patch("main.process_text", return_value=TextResult(
        word_count=3,
        page_count=1,
        paragraph_count=1,
        summary="Mocked summary",
        keywords=[KeywordItem(word="mock", score=1.0)],
        ai_model="test-mock"
    ))
    
    file_content = b"%PDF-1.4 Mock PDF Stream %%EOF"
    files = {"file": ("test.pdf", file_content, "application/pdf")}
    response = client.post("/api/upload", files=files)
    
    if response.status_code != 200:
        print("TEST ERROR DETAIL:", response.json())
        
    assert response.status_code == 200
    data = response.json()
    assert data["data_category"] == "text"
    assert data["text"]["summary"] == "Mocked summary"
    assert data["text"]["word_count"] == 3


def test_upload_valid_csv_endpoint(client, mocker):
    """Test uploading a valid CSV, mocking the internal parsers to avoid actual file system calls."""
    mocker.patch("parsers.csv_parser.parse_csv", return_value={"headers": ["Date", "Val"], "rows": [["2025-01-01", 10.0]]})

    file_content = b"Date,Val\n2025-01-01,10.0"
    files = {"file": ("test.csv", file_content, "text/csv")}
    response = client.post("/api/upload", files=files)

    assert response.status_code == 200
    data = response.json()
    assert data["file_type"] == "csv"
    assert data["data_category"] == "tabular"
    assert data["tabular"]["row_count"] == 1


def test_upload_valid_xlsx_endpoint(client, mocker):
    """Test uploading a valid XLSX spreadsheet."""
    mocker.patch("main.parse_xlsx", return_value={"headers": ["Region", "Sales"], "rows": [["North", 500.0]]})

    file_content = b"fake_xlsx_binary_content"
    files = {"file": ("sales.xlsx", file_content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
    response = client.post("/api/upload", files=files)

    assert response.status_code == 200
    data = response.json()
    assert data["file_type"] == "xlsx"
    assert data["data_category"] == "tabular"
    assert data["tabular"]["row_count"] == 1


def test_upload_valid_docx_endpoint(client, mocker):
    """Test uploading a valid DOCX file."""
    from models.schemas import TextResult, KeywordItem

    mocker.patch("main.parse_docx", return_value={"text": "Docx sample text", "paragraph_count": 2, "structured_tsv": ""})
    mocker.patch("main.extract_tables_from_text", return_value=None)
    mocker.patch("main.parse_tsv_grid", return_value=None)
    mocker.patch("main.process_text", return_value=TextResult(
        word_count=3,
        page_count=None,
        paragraph_count=2,
        summary="Docx summary",
        keywords=[KeywordItem(word="sample", score=0.95)],
        ai_model="test-mock"
    ))

    file_content = b"fake_docx_binary_stream"
    files = {"file": ("report.docx", file_content, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
    response = client.post("/api/upload", files=files)

    assert response.status_code == 200
    data = response.json()
    assert data["file_type"] == "docx"
    assert data["data_category"] == "text"
    assert data["text"]["summary"] == "Docx summary"


def test_upload_valid_txt_endpoint(client, mocker):
    """Test uploading a valid TXT document."""
    from models.schemas import TextResult, KeywordItem

    mocker.patch("main.parse_txt", return_value={"text": "Simple text content", "paragraph_count": 1})
    mocker.patch("main.extract_tables_from_text", return_value=None)
    mocker.patch("main.process_text", return_value=TextResult(
        word_count=3,
        page_count=None,
        paragraph_count=1,
        summary="Text summary",
        keywords=[KeywordItem(word="content", score=0.9)],
        ai_model="test-mock"
    ))

    file_content = b"Simple text content"
    files = {"file": ("notes.txt", file_content, "text/plain")}
    response = client.post("/api/upload", files=files)

    assert response.status_code == 200
    data = response.json()
    assert data["file_type"] == "txt"
    assert data["data_category"] == "text"
    assert data["text"]["summary"] == "Text summary"

def test_get_document_metrics_not_found(client, mocker):
    """Test retrieving metrics for a file that does not exist in the database."""
    mocker.patch("engine.db.get_metrics_by_file", return_value=[])
    response = client.get("/api/documents/non_existent.pdf/metrics")
    assert response.status_code == 404
    assert "No metrics found" in response.json()["detail"]

def test_get_document_metrics_success(client, mocker):
    """Test retrieving metrics successfully from the DuckDB database."""
    mock_metrics = [
        {
            "id": "1",
            "file_name": "test.pdf",
            "data_type": "metric",
            "category": "Revenue",
            "metric_value": 1000.0,
            "unit": "USD",
            "context_snippet": "Revenue was 1000 USD",
            "page_number": 1,
            "bbox": [10.0, 20.0, 30.0, 40.0],
            "page_width": 612.0,
            "page_height": 792.0,
            "created_at": "2026-07-23 12:00:00"
        }
    ]
    mocker.patch("engine.db.get_metrics_by_file", return_value=mock_metrics)
    response = client.get("/api/documents/test.pdf/metrics")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["category"] == "Revenue"
    assert data[0]["page_width"] == 612.0

def test_get_document_pdf_not_found(client, mocker):
    """Test retrieving PDF that does not exist on disk."""
    from pathlib import Path
    mocker.patch("main.DOCUMENTS_DIR", new=Path("/dummy_path"))
    response = client.get("/api/documents/non_existent.pdf/pdf")
    assert response.status_code == 404
    assert "Source PDF file not found" in response.json()["detail"]

