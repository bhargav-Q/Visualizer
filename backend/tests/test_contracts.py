"""
Contract Validation Tests — Phase 1 Verification
"""
import pytest
from contracts.document import DocumentContent, TableData, UnifiedDocumentModel
from contracts.profile import ColumnProfile, DocumentProfile
from contracts.charts import ChartSpec, ChartRecommendation
from context.pipeline_context import PipelineContext

def test_document_content_contract():
    content = DocumentContent(
        raw_text="Sample text",
        tables=[TableData(headers=["ColA", "ColB"], rows=[[1, 2], [3, 4]])],
        page_count=1
    )
    assert content.raw_text == "Sample text"
    assert len(content.tables) == 1
    assert content.tables[0].headers == ["ColA", "ColB"]

def test_unified_document_model_contract():
    model = UnifiedDocumentModel(
        filename="test.csv",
        file_type="csv",
        data_category="tabular",
        tables=[TableData(headers=["A"], rows=[[1]])],
        word_count=5
    )
    assert model.filename == "test.csv"
    assert model.data_category == "tabular"
    assert model.word_count == 5

def test_document_profile_contract():
    profile = DocumentProfile(
        filename="test.xlsx",
        file_type="xlsx",
        data_category="tabular",
        row_count=10,
        col_count=2,
        columns=[
            ColumnProfile(name="A", dtype="numeric", missing_count=0, unique_count=10, is_discrete=True)
        ]
    )
    assert profile.row_count == 10
    assert profile.columns[0].is_discrete is True

def test_chart_recommendation_contract():
    spec = ChartSpec(type="bar", title="Sample", x_key="Cat", y_key="Val", data=[{"Cat": "A", "Val": 10}])
    rec = ChartRecommendation(chart_type="bar", title="Sample", x_key="Cat", y_key="Val", chart_spec=spec)
    assert rec.chart_spec.type == "bar"
    assert rec.chart_spec.data[0]["Val"] == 10

def test_pipeline_context():
    ctx = PipelineContext(filename="sample.pdf", file_bytes=b"PDF")
    ctx.record_stage_time("parse", 12.5)
    ctx.add_warning("OCR sparse")
    assert ctx.filename == "sample.pdf"
    assert ctx.stage_timings_ms["parse"] == 12.5
    assert len(ctx.warnings) == 1
