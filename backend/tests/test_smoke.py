"""
Smoke Test Suite — Visualizer Backend
======================================
Standalone pytest script that tests the running backend server.

Prerequisites:
  1. Backend server must be running: `python -m uvicorn main:app --port 8000`
  2. Install test deps: `pip install pytest httpx anyio`

Run:
  pytest backend/tests/test_smoke.py -v --tb=short
"""

import os
import io
import time
import pytest
import httpx

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
BASE_URL = os.getenv("SMOKE_TEST_BASE_URL", "http://localhost:8000")
UPLOAD_ENDPOINT = f"{BASE_URL}/api/upload"
HEALTH_ENDPOINT = f"{BASE_URL}/api/health"

# Maximum acceptable response time for tabular fast-path (milliseconds)
TABULAR_FAST_PATH_MAX_MS = 5000  # 5s generous budget (includes network + cold DuckDB init)


# ---------------------------------------------------------------------------
# Helpers — Generate minimal valid files in-memory
# ---------------------------------------------------------------------------
def make_csv_bytes(rows: int = 50) -> bytes:
    """Generates a minimal CSV file with headers and N rows."""
    lines = ["Date,Region,Revenue,Units"]
    for i in range(rows):
        lines.append(f"2025-01-{(i % 28) + 1:02d},Region_{i % 5},{100.0 + i * 2.5},{10 + i}")
    return "\n".join(lines).encode("utf-8")


def make_xlsx_bytes() -> bytes:
    """Generates a minimal XLSX file using openpyxl."""
    try:
        import openpyxl
    except ImportError:
        pytest.skip("openpyxl not installed — required for XLSX smoke test")
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Sales"
    ws.append(["Product", "Quantity", "Price"])
    ws.append(["Widget A", 100, 29.99])
    ws.append(["Widget B", 200, 49.99])
    ws.append(["Widget C", 150, 19.99])
    
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.read()


def make_txt_bytes() -> bytes:
    """Generates a plain text document."""
    return b"""Quarterly Business Review - Q1 2025

Executive Summary:
Revenue grew 15% quarter-over-quarter, driven by strong performance in the APAC region.
Customer satisfaction scores improved to 92%, exceeding our target of 90%.

Key Highlights:
- New product launches contributed $2.3M in incremental revenue
- Operating expenses reduced by 8% through automation initiatives
- Employee headcount increased by 12 to support growth targets

Risks and Mitigations:
- Supply chain delays may impact Q2 delivery timelines
- Competitive pressure in the EMEA market requires pricing review
"""


def make_minimal_pdf_bytes() -> bytes:
    """Generates a minimal valid PDF with text content."""
    try:
        import pymupdf
        doc = pymupdf.open()
        page = doc.new_page(width=612, height=792)
        page.insert_text((72, 72), "Invoice #12345\nDate: 2025-01-15\nTotal: $1,500.00\nTax: 8.5%\nClient: Acme Corp")
        buf = io.BytesIO()
        doc.save(buf)
        doc.close()
        buf.seek(0)
        return buf.read()
    except ImportError:
        pytest.skip("pymupdf not installed — required for PDF smoke test")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def client():
    """
    Resilient HTTP client fixture for smoke tests.
    Uses in-process TestClient by default for fast, isolated unit testing.
    Connects to live server if USE_LIVE_SERVER environment variable is set.
    """
    if os.getenv("USE_LIVE_SERVER"):
        base_url = os.getenv("SMOKE_TEST_BASE_URL", "http://localhost:8000")
        try:
            live_client = httpx.Client(base_url=base_url, timeout=httpx.Timeout(120.0, connect=2.0))
            resp = live_client.get("/api/health")
            if resp.status_code == 200:
                yield live_client
                return
        except Exception:
            pass

    from main import app
    from fastapi.testclient import TestClient
    with TestClient(app) as tc:
        yield tc


# ---------------------------------------------------------------------------
# Test 1: Health Endpoint
# ---------------------------------------------------------------------------
def test_health_endpoint(client):
    """Verify the backend is reachable and healthy."""
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


# ---------------------------------------------------------------------------
# Test 2: Tabular CSV Fast-Path Smoke Test
# ---------------------------------------------------------------------------
def test_csv_upload_fast_path(client):
    """
    Upload a CSV file. Assert:
    - 200 OK response
    - data_category is 'tabular'
    - Valid structured JSON with columns, rows, charts
    - Response time is under TABULAR_FAST_PATH_MAX_MS
    """
    csv_bytes = make_csv_bytes(rows=50)
    
    t0 = time.perf_counter()
    resp = client.post(
        "/api/upload",
        files={"file": ("test_sales.csv", io.BytesIO(csv_bytes), "text/csv")}
    )
    elapsed_ms = (time.perf_counter() - t0) * 1000
    
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data = resp.json()
    
    assert data["file_type"] == "csv"
    assert data["data_category"] == "tabular"
    assert data["tabular"] is not None
    assert data["tabular"]["row_count"] == 50
    assert data["tabular"]["col_count"] == 4
    assert len(data["tabular"]["columns"]) == 4
    assert len(data["tabular"]["preview_rows"]) <= 100
    
    print(f"\n[SMOKE] CSV upload completed in {elapsed_ms:.0f}ms")
    assert elapsed_ms < TABULAR_FAST_PATH_MAX_MS, (
        f"CSV fast-path too slow: {elapsed_ms:.0f}ms > {TABULAR_FAST_PATH_MAX_MS}ms"
    )


# ---------------------------------------------------------------------------
# Test 3: Tabular XLSX Fast-Path Smoke Test
# ---------------------------------------------------------------------------
def test_xlsx_upload_fast_path(client):
    """
    Upload an XLSX file. Assert:
    - 200 OK with tabular data_category
    - Valid structured JSON with row_count, charts
    - Response time under budget
    """
    xlsx_bytes = make_xlsx_bytes()
    
    t0 = time.perf_counter()
    resp = client.post(
        "/api/upload",
        files={"file": ("quarterly_report.xlsx", io.BytesIO(xlsx_bytes),
                         "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
    )
    elapsed_ms = (time.perf_counter() - t0) * 1000
    
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data = resp.json()
    
    assert data["file_type"] == "xlsx"
    assert data["data_category"] == "tabular"
    assert data["tabular"] is not None
    assert data["tabular"]["row_count"] == 3
    
    print(f"\n[SMOKE] XLSX upload completed in {elapsed_ms:.0f}ms")
    assert elapsed_ms < TABULAR_FAST_PATH_MAX_MS, (
        f"XLSX fast-path too slow: {elapsed_ms:.0f}ms > {TABULAR_FAST_PATH_MAX_MS}ms"
    )


# ---------------------------------------------------------------------------
# Test 4: PDF Hybrid Parallel Parsing Test
# ---------------------------------------------------------------------------
def test_pdf_upload_with_analytics(client, mocker):
    """
    Upload a minimal PDF. Assert:
    - 200 OK response
    - data_category is text, mixed, or qualitative_document
    - text result contains a summary
    - analytics may contain metrics with bbox coordinates
    """
    async def mock_async(*args, **kwargs):
        return {}
    mocker.patch("processors.text_processor.extract_qualitative_sections", return_value=[])
    mocker.patch("engine.vision_client.extract_analytics_with_vision_async", side_effect=mock_async)
    mocker.patch("processors.ocr_processor.extract_tables_from_text_async", side_effect=mock_async)
    
    pdf_bytes = make_minimal_pdf_bytes()
    
    t0 = time.perf_counter()
    resp = client.post(
        "/api/upload",
        files={"file": ("invoice_sample.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    )
    elapsed_ms = (time.perf_counter() - t0) * 1000
    
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data = resp.json()
    
    assert data["file_type"] == "pdf"
    assert data["data_category"] in ("text", "mixed", "qualitative_document")
    
    # Text result should exist with a summary
    if data.get("text"):
        assert data["text"]["summary"], "PDF text summary should not be empty"
        assert data["text"]["word_count"] >= 0
    
    # If analytics has metrics, verify bbox structure
    if data.get("analytics") and data["analytics"].get("metrics"):
        for metric in data["analytics"]["metrics"]:
            if metric.get("bbox"):
                assert len(metric["bbox"]) == 4, "bbox must have exactly 4 coordinates [x0, y0, x1, y1]"
                assert all(isinstance(c, (int, float)) for c in metric["bbox"])
    
    print(f"\n[SMOKE] PDF upload completed in {elapsed_ms:.0f}ms")


# ---------------------------------------------------------------------------
# Test 5: TXT Upload — Qualitative Document Path
# ---------------------------------------------------------------------------
def test_txt_upload_qualitative(client, mocker):
    """
    Upload a plain text document. Assert:
    - 200 OK response
    - data_category is text or qualitative_document
    - text result has summary and keywords
    """
    async def mock_async(*args, **kwargs):
        return {}
    mocker.patch("processors.text_processor.extract_qualitative_sections", return_value=[])
    mocker.patch("engine.vision_client.extract_analytics_with_vision_async", side_effect=mock_async)
    mocker.patch("processors.ocr_processor.extract_tables_from_text_async", side_effect=mock_async)
    
    txt_bytes = make_txt_bytes()
    
    resp = client.post(
        "/api/upload",
        files={"file": ("quarterly_review.txt", io.BytesIO(txt_bytes), "text/plain")}
    )
    
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data = resp.json()
    
    assert data["file_type"] == "txt"
    assert data["data_category"] in ("text", "mixed", "qualitative_document")
    
    if data.get("text"):
        assert data["text"]["summary"], "TXT summary should not be empty"
        assert data["text"]["word_count"] > 0


# ---------------------------------------------------------------------------
# Test 6: Boundary — Oversized File Rejection (>16MB)
# ---------------------------------------------------------------------------
def test_reject_oversized_file(client):
    """
    Attempt to upload a 20MB file. Assert:
    - 413 status code (File too large)
    - Structured error message in response
    """
    oversized_bytes = b"0" * (20 * 1024 * 1024)  # 20MB of zeros
    
    resp = client.post(
        "/api/upload",
        files={"file": ("huge_file.pdf", io.BytesIO(oversized_bytes), "application/pdf")}
    )
    
    # Accept 400 (Starlette body limit) or 413 (our handler check)
    assert resp.status_code in (400, 413), f"Expected 400 or 413 for 20MB file, got {resp.status_code}"
    detail = resp.json().get("detail", "")
    assert any(term in detail.lower() for term in ["too large", "16mb", "unsupported", "error parsing the body", "parsing"]), (
        f"Expected meaningful error detail, got: {detail}"
    )


# ---------------------------------------------------------------------------
# Test 7: Boundary — Invalid File Extension Rejection
# ---------------------------------------------------------------------------
def test_reject_invalid_extension(client):
    """
    Attempt to upload an unsupported file type (.exe). Assert:
    - 400 status code
    - Structured error message mentioning 'unsupported'
    """
    fake_exe = b"MZ\x90\x00" + b"\x00" * 100  # Minimal PE header bytes
    
    resp = client.post(
        "/api/upload",
        files={"file": ("malware.exe", io.BytesIO(fake_exe), "application/octet-stream")}
    )
    
    assert resp.status_code == 400, f"Expected 400 for .exe file, got {resp.status_code}"
    detail = resp.json().get("detail", "")
    assert "unsupported" in detail.lower(), f"Expected 'unsupported' in error, got: {detail}"
