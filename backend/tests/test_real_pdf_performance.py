import os
import time
import pytest
from fastapi.testclient import TestClient
from main import app

def test_real_pdf_performance_and_caching():
    """
    Unmocked real-file integration benchmark:
    1. Loads an actual PDF ('real_complex_loss_run.pdf') from the test_files folder.
    2. Uploads the PDF to '/api/upload' and measures duration (ensuring it is within a real-world threshold).
    3. Re-uploads the same PDF and verifies the SHA-256 cache hit returns in < 500 milliseconds.
    """
    client = TestClient(app)
    
    # Path to real file in workspace
    real_pdf_path = os.path.join(os.path.dirname(__file__), "..", "..", "test_files", "real_complex_loss_run.pdf")
    
    # Ensure the test file exists
    assert os.path.exists(real_pdf_path), f"Test file not found at {real_pdf_path}"
    
    with open(real_pdf_path, "rb") as f:
        file_bytes = f.read()
    
    # First Upload (Cold Start - Full parsing/extraction/fallback)
    t0 = time.perf_counter()
    response = client.post(
        "/api/upload",
        files={"file": ("real_complex_loss_run.pdf", file_bytes, "application/pdf")}
    )
    duration_cold = time.perf_counter() - t0
    
    assert response.status_code == 200, f"Cold upload failed: {response.text}"
    data_cold = response.json()
    assert data_cold["file_name"] == "real_complex_loss_run.pdf"
    assert data_cold["file_type"] == "pdf"
    assert data_cold["data_category"] in ("text", "mixed")
    
    # Assert cold processing completed within an acceptable threshold (e.g. under 120 seconds for API retry timeouts)
    print(f"\n[BENCHMARK] Cold start upload completed in: {duration_cold:.4f}s")
    assert duration_cold < 120.0, f"Cold upload was too slow: took {duration_cold:.2f} seconds"
    
    # Second Upload (Warm Start - SHA-256 Cache Hit)
    t1 = time.perf_counter()
    response_warm = client.post(
        "/api/upload",
        files={"file": ("real_complex_loss_run.pdf", file_bytes, "application/pdf")}
    )
    duration_warm = time.perf_counter() - t1
    
    assert response_warm.status_code == 200, f"Warm upload failed: {response_warm.text}"
    data_warm = response_warm.json()
    assert data_warm["file_name"] == "real_complex_loss_run.pdf"
    
    # Assert cache hit returns in under 500ms
    print(f"[BENCHMARK] Warm start cache hit completed in: {duration_warm:.4f}s")
    assert duration_warm < 0.5, f"Cache hit took too long: {duration_warm:.4f} seconds"
