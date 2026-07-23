import pytest
import os
import tempfile
from fastapi import UploadFile
from io import BytesIO

from engine.pydantic_models import DocumentAnalytics, ExtractedMetric, KeyValuePair, ExtractedTable
from engine.db import init_db, save_document_analytics, get_metrics_by_file, get_analytics_summary
from engine.document_extractor import match_text_to_bbox, create_heuristic_fallback_analytics, process_unstructured_document

def test_pydantic_document_analytics_schema():
    """Tests Pydantic validation for all data types."""
    metric = ExtractedMetric(
        category="Q2 Revenue",
        metric_value=150000.50,
        unit="USD",
        context_snippet="Q2 Revenue reached $150,000.50 in APAC region.",
        page_number=1,
        bbox=[10.0, 20.0, 100.0, 50.0]
    )
    kv = KeyValuePair(
        key_name="Tax ID",
        value="TX-998231",
        context_snippet="Tax ID: TX-998231 registered in US.",
        page_number=1
    )
    tbl = ExtractedTable(
        table_title="Sales Summary",
        headers=["Region", "Sales"],
        rows=[["North", "500"]],
        page_number=1
    )
    analytics = DocumentAnalytics(
        document_title="Q2 Financial Report",
        report_date="2025-06-30",
        summary="Company achieved record sales in Q2 2025.",
        keywords=["revenue", "apac", "financial"],
        metrics=[metric],
        key_value_pairs=[kv],
        tables=[tbl]
    )

    assert analytics.document_title == "Q2 Financial Report"
    assert len(analytics.metrics) == 1
    assert analytics.metrics[0].metric_value == 150000.50
    assert analytics.metrics[0].bbox == [10.0, 20.0, 100.0, 50.0]
    assert len(analytics.key_value_pairs) == 1
    assert analytics.key_value_pairs[0].key_name == "Tax ID"

def test_resilient_field_coercion():
    """Tests field validator coercion for non-float strings and float matrix cells."""
    # 1. Non-numeric metric values coerce to 0.0 or float
    m1 = ExtractedMetric(category="Type", metric_value="Wholesale", context_snippet="Type: Wholesale")
    assert m1.metric_value == 0.0

    m2 = ExtractedMetric(category="Revenue", metric_value="$12,345.67 USD", context_snippet="Rev")
    assert m2.metric_value == 12345.67

    # 2. Matrix cell float/int values coerce to str
    tbl = ExtractedTable(
        headers=["Col1", "Col2"],
        rows=[[12345.67, 0.15], ["Item A", 100]]
    )
    assert tbl.rows == [["12345.67", "0.15"], ["Item A", "100"]]

def test_duckdb_storage_layer():
    """Tests DuckDB app_data.duckdb table creation, insertion, and retrieval."""
    init_db()

    test_file = "test_financial_report.pdf"
    analytics = DocumentAnalytics(
        document_title="Test Report",
        report_date="2025-01-01",
        summary="Test report summary.",
        keywords=["test", "report"],
        metrics=[
            ExtractedMetric(
                category="Net Profit",
                metric_value=45000.0,
                unit="USD",
                context_snippet="Net Profit was $45,000.",
                page_number=1,
                bbox=[15.0, 25.0, 120.0, 60.0]
            )
        ],
        key_value_pairs=[
            KeyValuePair(key_name="Account Status", value="Active", context_snippet="Account Status: Active", page_number=1)
        ],
        tables=[]
    )

    inserted = save_document_analytics(test_file, analytics)
    assert inserted >= 2

    saved_rows = get_metrics_by_file(test_file)
    assert len(saved_rows) >= 2
    
    metric_row = next((r for r in saved_rows if r["data_type"] == "metric"), None)
    assert metric_row is not None
    assert metric_row["category"] == "Net Profit"
    assert metric_row["metric_value"] == 45000.0
    assert metric_row["bbox"] == [15.0, 25.0, 120.0, 60.0]

    summary_stats = get_analytics_summary()
    assert summary_stats["total_files"] >= 1
    assert summary_stats["total_metrics"] >= 1

def test_text_to_bbox_matching():
    """Tests matching context snippet to PyMuPDF spatial bounding boxes."""
    blocks = [
        {"bbox": [10.0, 10.0, 200.0, 40.0], "text": "Annual Operating Expense: $120,000 USD"},
        {"bbox": [10.0, 50.0, 200.0, 80.0], "text": "Quarterly Headcount: 45 Employees"}
    ]

    bbox = match_text_to_bbox(blocks, "Annual Operating Expense")
    assert bbox == [10.0, 10.0, 200.0, 40.0]

    bbox_headcount = match_text_to_bbox(blocks, "Headcount: 45")
    assert bbox_headcount == [10.0, 50.0, 200.0, 80.0]

    bbox_none = match_text_to_bbox(blocks, "Non-existent phrase")
    assert bbox_none is None

def test_heuristic_fallback_analytics():
    """Tests creating analytics fallback from raw unstructured text."""
    raw_text = """
    Company Q1 Status Report
    Revenue: $250,000 USD
    Operating Expenses: $80,000 USD
    Status: Approved
    """
    analytics = create_heuristic_fallback_analytics("sample_report.txt", raw_text)
    assert analytics.document_title == "sample_report.txt"
    assert len(analytics.metrics) >= 1
    assert any(m.metric_value == 250000.0 for m in analytics.metrics)
    assert len(analytics.key_value_pairs) >= 1

def test_process_unstructured_document_txt_file():
    """Tests processing TXT file through entrypoint and persisting to DuckDB."""
    file_bytes = b"Revenue: $500,000 USD\nExpense: $100,000 USD\nStatus: Complete"
    upload_file = UploadFile(filename="annual_summary.txt", file=BytesIO(file_bytes))

    result = process_unstructured_document(upload_file)

    assert result["file_name"] == "annual_summary.txt"
    assert result["duckdb_persisted"] is True
    assert result["records_inserted"] > 0
    assert "metrics" in result["analytics"]
