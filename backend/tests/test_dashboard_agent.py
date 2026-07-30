import pytest
from services.dashboard_agent import generate_dashboard_spec_from_markdown, extract_local_keywords, generate_heuristic_fallback_dashboard_spec

def test_extract_local_keywords():
    sample_text = "Java Spring Boot React Microservices REST APIs SQL Docker Kubernetes Java Spring Boot"
    keywords = extract_local_keywords(sample_text, top_n=5)
    assert isinstance(keywords, list)
    assert len(keywords) > 0
    words = [k["word"] for k in keywords]
    assert "Java" in words or "Spring" in words
    for item in keywords:
        assert "word" in item
        assert "score" in item
        assert 0.0 <= item["score"] <= 1.0

def test_heuristic_fallback_dashboard_spec():
    sample_md = "# Quarterly Financial Report\nTotal Revenue: $4.2M across 12 Pages.\n\n| Year | Sales |\n| 2025 | 100 |"
    spec = generate_heuristic_fallback_dashboard_spec(sample_md)
    assert spec["dashboard_title"] == "Quarterly Financial Report"
    assert "kpis" in spec
    assert "keywords" in spec
    assert isinstance(spec["keywords"], list)

def test_generate_dashboard_spec_from_markdown():
    sample_md = "# Curriculum Overview\nTopics: Java, Spring Boot, Microservices.\n\n| Module | Duration |\n| Core Java | 4 Weeks |"
    spec = generate_dashboard_spec_from_markdown(sample_md)
    assert "dashboard_title" in spec
    assert "executive_summary" in spec
    assert "kpis" in spec
    assert "charts" in spec
    assert isinstance(spec["kpis"], list)
    assert isinstance(spec["charts"], list)
