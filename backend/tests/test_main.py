import pytest
from io import BytesIO

def test_upload_invalid_file_type(client):
    """Test that a .txt file is rejected."""
    file_content = b"Some text data"
    files = {"file": ("test.txt", file_content, "text/plain")}
    response = client.post("/api/upload", files=files)
    
    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]

def test_upload_file_too_large(client, mocker):
    """Test that a >15MB file is rejected."""
    # We can fake the size check by mocking the seek/tell mechanism in main.py
    # or just create a 16MB string in memory (might be slow but it's fine)
    # Actually, main.py checks `file.file.seek(0, 2)` then `file.file.tell()`
    # Let's mock `fastapi.UploadFile` file size or just send 15MB + 1 byte
    
    large_content = b"0" * (15 * 1024 * 1024 + 1)
    files = {"file": ("large.pdf", large_content, "application/pdf")}
    response = client.post("/api/upload", files=files)
    
    assert response.status_code == 413
    assert "File too large" in response.json()["detail"]

def test_upload_valid_pdf_endpoint(client, mocker):
    """Test uploading a valid PDF, mocking the internal parsers to avoid API calls."""
    # Mock the parser and processor
    mocker.patch("parsers.pdf_parser.parse_pdf", return_value={"text": "Mocked PDF text", "page_count": 1})
    mocker.patch("processors.text_processor.process_text", return_value={
        "word_count": 3,
        "page_count": 1,
        "paragraph_count": 1,
        "summary": "Mocked summary",
        "keywords": [{"word": "mock", "score": 1.0}],
        "ai_model": "test-mock"
    })
    
    file_content = b"Fake PDF binary"
    files = {"file": ("test.pdf", file_content, "application/pdf")}
    response = client.post("/api/upload", files=files)
    
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
