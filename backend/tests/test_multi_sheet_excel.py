"""
Unit and Integration Tests for Multi-Worksheet Excel Workbook Analysis
"""
import pytest
from unittest.mock import MagicMock
import io

from contracts.document import DocumentContent, TableData, UnifiedDocumentModel
from processors.profiler import DataProfiler
from processors.recommender import VisualizationRecommender
from services.dashboard_builder import DashboardBuilder


def _make_multi_sheet_model():
    """Helper: Create a UnifiedDocumentModel with 3 worksheets."""
    tables = [
        TableData(
            table_title="Sheet: Sales",
            headers=["Region", "Product", "Revenue", "Units"],
            rows=[
                ["North", "Widget A", 15000, 120],
                ["South", "Widget B", 22000, 200],
                ["East", "Widget A", 18000, 150],
                ["West", "Widget C", 9000, 80],
            ],
            page_number=1
        ),
        TableData(
            table_title="Sheet: Expenses",
            headers=["Department", "Category", "Amount"],
            rows=[
                ["Engineering", "Salaries", 85000],
                ["Marketing", "Ads", 12000],
                ["Engineering", "Cloud", 5000],
                ["Sales", "Travel", 8000],
            ],
            page_number=1
        ),
        TableData(
            table_title="Sheet: Payroll",
            headers=["Employee", "Role", "Salary", "Bonus"],
            rows=[
                ["Alice", "Engineer", 95000, 5000],
                ["Bob", "Designer", 80000, 3000],
                ["Charlie", "Manager", 110000, 10000],
            ],
            page_number=1
        ),
    ]

    return UnifiedDocumentModel(
        filename="multi_sheet_sample.xlsx",
        file_type="xlsx",
        data_category="tabular",
        raw_text="",
        tables=tables,
        metadata={"sheet_count": 3}
    )


def _make_single_sheet_model():
    """Helper: Create a UnifiedDocumentModel with 1 worksheet."""
    tables = [
        TableData(
            table_title="Sheet: Data",
            headers=["Name", "Score"],
            rows=[
                ["Alice", 95],
                ["Bob", 88],
            ],
            page_number=1
        ),
    ]
    return UnifiedDocumentModel(
        filename="single_sheet.xlsx",
        file_type="xlsx",
        data_category="tabular",
        raw_text="",
        tables=tables,
        metadata={"sheet_count": 1}
    )


# ─── Profiler Tests ───

class TestMultiSheetProfiler:
    def test_profiles_primary_table(self):
        model = _make_multi_sheet_model()
        profile = DataProfiler.profile(model)
        assert profile.row_count == 4
        assert profile.col_count == 4
        assert len(profile.columns) == 4

    def test_sheet_profiles_attached(self):
        model = _make_multi_sheet_model()
        profile = DataProfiler.profile(model)
        sheet_profiles = profile.metadata.get("sheet_profiles", [])
        assert len(sheet_profiles) == 3

    def test_sheet_profile_names(self):
        model = _make_multi_sheet_model()
        profile = DataProfiler.profile(model)
        sheet_profiles = profile.metadata.get("sheet_profiles", [])
        names = [sp["sheet_name"] for sp in sheet_profiles]
        assert "Sales" in names
        assert "Expenses" in names
        assert "Payroll" in names

    def test_sheet_profile_row_counts(self):
        model = _make_multi_sheet_model()
        profile = DataProfiler.profile(model)
        sheet_profiles = profile.metadata.get("sheet_profiles", [])
        counts = {sp["sheet_name"]: sp["row_count"] for sp in sheet_profiles}
        assert counts["Sales"] == 4
        assert counts["Expenses"] == 4
        assert counts["Payroll"] == 3

    def test_single_sheet_no_sheet_profiles(self):
        """Single-sheet workbooks should NOT have sheet_profiles metadata."""
        model = _make_single_sheet_model()
        profile = DataProfiler.profile(model)
        sheet_profiles = (profile.metadata or {}).get("sheet_profiles", [])
        assert len(sheet_profiles) == 0

    def test_numeric_summaries_per_sheet(self):
        model = _make_multi_sheet_model()
        profile = DataProfiler.profile(model)
        sheet_profiles = profile.metadata.get("sheet_profiles", [])
        payroll = [sp for sp in sheet_profiles if sp["sheet_name"] == "Payroll"][0]
        assert "Salary" in payroll["numeric_summaries"]
        assert "Bonus" in payroll["numeric_summaries"]


# ─── Dashboard Builder Tests ───

class TestMultiSheetDashboardBuilder:
    def test_response_contains_sheets(self):
        model = _make_multi_sheet_model()
        profile = DataProfiler.profile(model)
        recommendations = VisualizationRecommender.recommend(profile, model)
        response = DashboardBuilder.build_response(model, profile, recommendations)

        assert response.tabular is not None
        assert len(response.tabular.sheets) == 3

    def test_sheet_names_in_response(self):
        model = _make_multi_sheet_model()
        profile = DataProfiler.profile(model)
        recommendations = VisualizationRecommender.recommend(profile, model)
        response = DashboardBuilder.build_response(model, profile, recommendations)

        sheet_names = [s.sheet_name for s in response.tabular.sheets]
        assert "Sales" in sheet_names
        assert "Expenses" in sheet_names
        assert "Payroll" in sheet_names

    def test_per_sheet_preview_rows(self):
        model = _make_multi_sheet_model()
        profile = DataProfiler.profile(model)
        recommendations = VisualizationRecommender.recommend(profile, model)
        response = DashboardBuilder.build_response(model, profile, recommendations)

        for sheet in response.tabular.sheets:
            assert len(sheet.preview_rows) > 0
            assert sheet.row_count > 0
            assert sheet.col_count > 0

    def test_per_sheet_columns(self):
        model = _make_multi_sheet_model()
        profile = DataProfiler.profile(model)
        recommendations = VisualizationRecommender.recommend(profile, model)
        response = DashboardBuilder.build_response(model, profile, recommendations)

        payroll = [s for s in response.tabular.sheets if s.sheet_name == "Payroll"][0]
        col_names = [c.name for c in payroll.columns]
        assert "Employee" in col_names
        assert "Salary" in col_names

    def test_single_sheet_empty_sheets_array(self):
        """Single-sheet workbooks should have empty sheets array (backward compatible)."""
        model = _make_single_sheet_model()
        profile = DataProfiler.profile(model)
        recommendations = VisualizationRecommender.recommend(profile, model)
        response = DashboardBuilder.build_response(model, profile, recommendations)

        assert response.tabular is not None
        assert len(response.tabular.sheets) == 0
        # Primary data should still be present
        assert response.tabular.row_count == 2
        assert len(response.tabular.columns) == 2

    def test_response_serializable(self):
        """Ensure the full response can be serialized to JSON without errors."""
        model = _make_multi_sheet_model()
        profile = DataProfiler.profile(model)
        recommendations = VisualizationRecommender.recommend(profile, model)
        response = DashboardBuilder.build_response(model, profile, recommendations)

        json_out = response.model_dump_json()
        assert '"sheets"' in json_out
        assert '"Sales"' in json_out
