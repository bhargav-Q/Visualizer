from typing import List, Optional, Any, Dict
from contracts.document import UnifiedDocumentModel
from contracts.profile import DocumentProfile, ColumnProfile
from contracts.charts import ChartRecommendation, ChartSpec
from models.schemas import (
    UploadResponse, TabularResult, ColumnInfo, ChartData, TextResult,
    DocumentAnalyticsResponse, SheetData, NumericSummary, CategoricalSummary
)

class DashboardBuilder:
    """Assembles UploadResponse schema objects from PipelineContext artifacts for frontend presentation."""

    @staticmethod
    def _build_charts_for_sheet(sheet_profile: dict) -> List[ChartData]:
        """Generate chart recommendations for a single sheet profile."""
        charts = []
        columns = sheet_profile.get("columns", [])
        rows = sheet_profile.get("rows", [])
        headers = sheet_profile.get("headers", [])
        num_summaries = sheet_profile.get("numeric_summaries", {})

        if not rows or not headers:
            return charts

        num_cols = list(num_summaries.keys())
        cat_cols = [c.name for c in columns if c.dtype == "string" and 1 <= c.unique_count <= 50]

        # Build column data map
        col_data = {h: [] for h in headers}
        for row in rows:
            for i, h in enumerate(headers):
                val = row[i] if i < len(row) else None
                col_data[h].append(val)

        def sanitize_key(k: str) -> str:
            return str(k).replace("/", " ").replace(",", " ").replace(".", " ").strip()

        # Bar charts: categorical x numeric
        for x_col in cat_cols[:2]:
            if len(charts) >= 2:
                break
            for num_col in num_cols[:2]:
                if len(charts) >= 2:
                    break
                if x_col == num_col:
                    continue
                clean_x = sanitize_key(x_col)
                clean_y = sanitize_key(num_col)
                grouped = {}
                counts = {}
                for x_val, n_val in zip(col_data.get(x_col, []), col_data.get(num_col, [])):
                    if x_val is not None and n_val is not None:
                        try:
                            x_str = str(x_val)
                            n_float = float(str(n_val).replace("$", "").replace(",", ""))
                            grouped[x_str] = grouped.get(x_str, 0.0) + n_float
                            counts[x_str] = counts.get(x_str, 0) + 1
                        except (ValueError, TypeError):
                            pass
                if grouped:
                    averages = {k: grouped[k] / counts[k] for k in grouped}
                    sorted_top = sorted(averages.items(), key=lambda item: item[1], reverse=True)[:10]
                    chart_data = [{clean_x: k, clean_y: round(v, 2)} for k, v in sorted_top]
                    charts.append(ChartData(
                        type="bar",
                        title=f"Average {clean_y} by {clean_x}",
                        x_key=clean_x,
                        y_key=clean_y,
                        data=chart_data
                    ))

        # Fallback: row index line chart
        if not charts and num_cols:
            num_col = num_cols[0]
            clean_y = sanitize_key(num_col)
            chart_data = []
            for idx, val in enumerate(col_data.get(num_col, [])[:100]):
                if val is not None:
                    try:
                        chart_data.append({"Row Index": idx + 1, clean_y: float(str(val).replace("$", "").replace(",", ""))})
                    except (ValueError, TypeError):
                        pass
            if chart_data:
                charts.append(ChartData(
                    type="line",
                    title=f"{clean_y} by Row Index",
                    x_key="Row Index",
                    y_key=clean_y,
                    data=chart_data
                ))

        return charts

    @staticmethod
    def build_response(
        model: UnifiedDocumentModel,
        profile: DocumentProfile,
        recommendations: List[ChartRecommendation],
        analytics: Optional[Any] = None,
        processing_time: float = 0.0
    ) -> UploadResponse:
        
        # Build TabularResult if primary table exists
        tabular_result: Optional[TabularResult] = None
        if model.tables and model.tables[0].rows:
            table = model.tables[0]
            if profile and getattr(profile, "columns", None):
                columns = [ColumnInfo(name=c.name, dtype=getattr(c, "dtype", "string")) for c in profile.columns]
            else:
                columns = [ColumnInfo(name=str(h), dtype="string") for h in getattr(table, "headers", [])]
            
            # Serialize preview rows (up to 100 rows)
            preview_rows = table.rows[:100]

            charts: List[ChartData] = []
            if recommendations:
                for rec in recommendations:
                    spec = getattr(rec, "chart_spec", rec)
                    charts.append(ChartData(
                        type=getattr(spec, "type", "bar"),
                        title=getattr(spec, "title", "Chart"),
                        x_key=getattr(spec, "x_key", ""),
                        y_key=getattr(spec, "y_key", ""),
                        data=getattr(spec, "data", [])
                    ))

            row_count = getattr(profile, "row_count", len(table.rows)) if profile else len(table.rows)
            col_count = getattr(profile, "col_count", len(columns)) if profile else len(columns)

            numeric_summary = getattr(profile, "numeric_summaries", {}) if profile else {}
            categorical_summary = getattr(profile, "categorical_summaries", {}) if profile else {}

            # Build per-sheet data from profile metadata
            sheets: List[SheetData] = []
            sheet_profiles = (profile.metadata or {}).get("sheet_profiles", []) if profile else []
            
            if sheet_profiles and len(sheet_profiles) > 1:
                for sp in sheet_profiles:
                    sp_columns = [ColumnInfo(name=c.name, dtype=c.dtype) for c in sp["columns"]]
                    sp_preview = sp["rows"][:100] if sp.get("rows") else []
                    sp_num = {}
                    for k, v in sp.get("numeric_summaries", {}).items():
                        if isinstance(v, NumericSummary):
                            sp_num[k] = v
                        elif isinstance(v, dict):
                            sp_num[k] = NumericSummary(**v)
                    sp_cat = {}
                    for k, v in sp.get("categorical_summaries", {}).items():
                        if isinstance(v, CategoricalSummary):
                            sp_cat[k] = v
                        elif isinstance(v, dict):
                            sp_cat[k] = CategoricalSummary(**v)

                    # Generate per-sheet charts
                    sp_charts = DashboardBuilder._build_charts_for_sheet(sp)

                    sheets.append(SheetData(
                        sheet_name=sp["sheet_name"],
                        columns=sp_columns,
                        preview_rows=sp_preview,
                        row_count=sp.get("row_count", len(sp.get("rows", []))),
                        col_count=sp.get("col_count", len(sp_columns)),
                        numeric_summary=sp_num,
                        categorical_summary=sp_cat,
                        charts=sp_charts
                    ))

            tabular_result = TabularResult(
                columns=columns,
                preview_rows=preview_rows,
                row_count=row_count,
                col_count=col_count,
                numeric_summary=numeric_summary,
                categorical_summary=categorical_summary,
                charts=charts,
                sheets=sheets
            )

        # Build TextResult if text content exists
        text_result: Optional[TextResult] = None
        if getattr(model, "raw_text", None):
            raw_text_val = model.raw_text or ""
            text_result = TextResult(
                summary=getattr(profile, "summary", f"Summary preview: {raw_text_val[:200]}") if profile else f"Summary preview: {raw_text_val[:200]}",
                keywords=getattr(profile, "keywords", []) if profile else [],
                word_count=getattr(profile, "word_count", len(raw_text_val.split())) if profile else len(raw_text_val.split()),
                page_count=getattr(model, "page_count", 1) or 1,
                paragraph_count=getattr(model, "paragraph_count", 1) or 1,
                ai_model="pipeline-v2"
            )

        # Convert analytics if present
        analytics_response: Optional[DocumentAnalyticsResponse] = None
        if analytics:
            if hasattr(analytics, "model_dump"):
                analytics_response = DocumentAnalyticsResponse(**analytics.model_dump())
            elif isinstance(analytics, dict):
                analytics_response = DocumentAnalyticsResponse(**analytics)

        return UploadResponse(
            file_name=model.filename,
            file_type=model.file_type,
            data_category=model.data_category,
            tabular=tabular_result,
            text=text_result,
            analytics=analytics_response,
            processing_time=round(processing_time, 2)
        )
