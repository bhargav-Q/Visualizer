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

def test_dashboard_spec_schema_validation_success():
    from services.dashboard_agent import DashboardSpecValidationSchema
    valid_spec = {
        "dashboard_title": "Test Title",
        "executive_summary": "Test Summary",
        "kpis": [{"label": "Revenue", "value": "$100", "page_range": "Page 1"}],
        "key_value_pairs": [{"key_name": "Date", "value": "2025-10-04", "page_number": 1}],
        "keywords": [{"word": "Revenue", "score": 0.9}],
        "charts": [{
            "title": "Sales Chart",
            "chart_type": "bar",
            "x_axis_label": "Year",
            "y_axis_label": "Amount",
            "x_data": ["2023", "2024"],
            "y_data": [100, 200],
            "page_range": "Page 1"
        }]
    }
    validated = DashboardSpecValidationSchema(**valid_spec)
    assert validated.dashboard_title == "Test Title"
    assert len(validated.charts) == 1
    assert validated.charts[0].y_data == [100, 200]

def test_dashboard_spec_charts_as_string_fails_validation():
    from pydantic import ValidationError
    from services.dashboard_agent import DashboardSpecValidationSchema
    invalid_spec = {
        "dashboard_title": "Test Title",
        "executive_summary": "Test Summary",
        "charts": "None"
    }
    with pytest.raises(ValidationError):
        DashboardSpecValidationSchema(**invalid_spec)

def test_dashboard_spec_non_numeric_y_data_fails_validation():
    from pydantic import ValidationError
    from services.dashboard_agent import DashboardSpecValidationSchema
    invalid_spec = {
        "dashboard_title": "Test Title",
        "executive_summary": "Test Summary",
        "charts": [{
            "title": "Sales Chart",
            "chart_type": "bar",
            "x_data": ["Q1", "Q2"],
            "y_data": ["100", "N/A"]
        }]
    }
    with pytest.raises(ValidationError):
        DashboardSpecValidationSchema(**invalid_spec)
