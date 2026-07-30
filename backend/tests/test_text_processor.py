import pytest
from services.text_processor import process_extracted_text_for_llm

def test_process_extracted_text_page_chunks():
    sample_md = "## Page 1\nContent for page 1\n\n---\n\n## Page 2\nContent for page 2"
    chunks = process_extracted_text_for_llm(sample_md)
    assert isinstance(chunks, list)
    assert len(chunks) >= 1
    assert isinstance(chunks[0], str)
    assert "Page 1" in chunks[0]

def test_process_extracted_text_single_page():
    sample_md = "Single page document text without page breaks."
    chunks = process_extracted_text_for_llm(sample_md)
    assert len(chunks) == 1
    assert isinstance(chunks[0], str)
    assert "Single page document" in chunks[0]
