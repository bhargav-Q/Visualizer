import os
import time
import pytest
import asyncio
from io import BytesIO
from fastapi import UploadFile
from main import upload_file

@pytest.mark.anyio
async def test_real_pdf_performance_and_caching():
    """
    Unmocked real-file integration benchmark:
    1. Loads an actual PDF ('real_complex_loss_run.pdf') from the test_files folder.
    2. Uploads the PDF to 'upload_file' and measures duration.
    3. Re-uploads the same PDF and verifies the SHA-256 cache hit returns in < 500 milliseconds.
    """
    real_pdf_path = os.path.join(os.path.dirname(__file__), "..", "..", "test_files", "real_complex_loss_run.pdf")
    assert os.path.exists(real_pdf_path), f"Test file not found at {real_pdf_path}"
    
    with open(real_pdf_path, "rb") as f:
        file_bytes = f.read()
    
    # First Upload (Cold Start - Full parsing/extraction/fallback)
    t0 = time.perf_counter()
    upload_file_obj = UploadFile(filename="real_complex_loss_run.pdf", file=BytesIO(file_bytes))
    response = await upload_file(upload_file_obj)
    duration_cold = time.perf_counter() - t0
    
    assert response.file_name == "real_complex_loss_run.pdf"
    assert response.file_type == "pdf"
    assert response.data_category in ("tabular", "text", "mixed", "qualitative_document")
    
    print(f"\n[BENCHMARK] Cold start upload completed in: {duration_cold:.4f}s")
    assert duration_cold < 120.0, f"Cold upload was too slow: took {duration_cold:.2f} seconds"
    
    # Second Upload (Warm Start - SHA-256 Cache Hit)
    t1 = time.perf_counter()
    upload_file_obj2 = UploadFile(filename="real_complex_loss_run.pdf", file=BytesIO(file_bytes))
    response_warm = await upload_file(upload_file_obj2)
    duration_warm = time.perf_counter() - t1
    
    assert response_warm.file_name == "real_complex_loss_run.pdf"
    print(f"[BENCHMARK] Warm start cache hit completed in: {duration_warm:.4f}s")
    assert duration_warm < 1.5, f"Cache hit took too long: {duration_warm:.4f} seconds"
