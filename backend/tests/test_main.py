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
