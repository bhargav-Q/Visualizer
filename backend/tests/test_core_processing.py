"""
Core Processing Test Suite — Milestone 2 Verification
"""
import pytest
from contracts.document import DocumentContent, TableData
from processors.normalizer import DocumentNormalizer
from processors.enricher import DocumentEnricher
from processors.profiler import DataProfiler
from processors.recommender import VisualizationRecommender

def test_document_normalizer():
    raw_content = DocumentContent(
        raw_text="",
        tables=[TableData(headers=["Date", "Revenue"], rows=[["2025-01-01", 100], ["2025-01-02", 150]])]
    )
    model = DocumentNormalizer.normalize(raw_content, "sales.csv", "csv")
    assert model.data_category == "tabular"
    assert len(model.tables) == 1
    assert model.tables[0].headers == ["Date", "Revenue"]

def test_document_enricher():
    raw_content = DocumentContent(
        raw_text="HeaderA\tHeaderB\nValA1\t100\nValA2\t200",
        tables=[]
    )
    model = DocumentNormalizer.normalize(raw_content, "text_table.txt", "txt")
    enriched = DocumentEnricher.enrich(model)
    assert len(enriched.tables) == 1
    assert enriched.tables[0].headers == ["HeaderA", "HeaderB"]

def test_data_profiler_and_recommender():
    raw_content = DocumentContent(
        raw_text="",
        tables=[TableData(headers=["Region", "Sales"], rows=[["North", 500], ["South", 300], ["North", 400]])]
    )
    model = DocumentNormalizer.normalize(raw_content, "region.csv", "csv")
    profile = DataProfiler.profile(model)
    
    assert profile.row_count == 3
    assert profile.col_count == 2
    assert "Sales" in profile.numeric_summaries
    assert profile.numeric_summaries["Sales"].mean == 400.0

    recs = VisualizationRecommender.recommend(profile, model)
    assert len(recs) >= 1
    assert recs[0].chart_type == "bar"
    assert recs[0].x_key == "Region"
    assert recs[0].y_key == "Sales"
