from typing import List
from contracts.document import UnifiedDocumentModel
from contracts.profile import DocumentProfile
from contracts.charts import ChartRecommendation, ChartSpec

class VisualizationRecommender:
    """Rule-based engine recommending optimal visual charts based on DocumentProfile metadata."""

    @staticmethod
    def recommend(profile: DocumentProfile, model: UnifiedDocumentModel) -> List[ChartRecommendation]:
        recommendations: List[ChartRecommendation] = []

        if not model.tables or not model.tables[0].rows:
            return recommendations

        table = model.tables[0]
        headers = table.headers
        rows = table.rows

        # Build column map for easy data extraction
        col_data = {h: [] for h in headers}
        for row in rows:
            for i, h in enumerate(headers):
                val = row[i] if i < len(row) else None
                col_data[h].append(val)

        num_cols = list(profile.numeric_summaries.keys())
        date_cols = [c.name for c in profile.columns if c.dtype == "datetime"]
        cat_cols = [c.name for c in profile.columns if c.dtype == "string" and 1 <= c.unique_count <= 50]
        discrete_num_cols = [c.name for c in profile.columns if c.is_discrete]

        x_candidates = cat_cols + discrete_num_cols

        def sanitize_key(k: str) -> str:
            return str(k).replace("/", " ").replace(",", " ").replace(".", " ").strip()

        # Rule 1: Time-series Line Chart Recommendations
        for date_col in date_cols[:2]:
            for num_col in num_cols[:2]:
                if date_col == num_col:
                    continue
                clean_x = sanitize_key(date_col)
                clean_y = sanitize_key(num_col)
                if clean_x == clean_y:
                    clean_y = f"{clean_y} (val)"

                chart_data = []
                for d_val, n_val in zip(col_data[date_col], col_data[num_col]):
                    if d_val is not None and n_val is not None:
                        try:
                            chart_data.append({clean_x: str(d_val)[:10], clean_y: float(n_val)})
                        except (ValueError, TypeError):
                            pass

                if chart_data:
                    spec = ChartSpec(type="line", title=f"Total {clean_y} over Time", x_key=clean_x, y_key=clean_y, data=chart_data[:100])
                    recommendations.append(ChartRecommendation(
                        chart_type="line",
                        title=f"Total {clean_y} over Time",
                        x_key=clean_x,
                        y_key=clean_y,
                        score=0.95,
                        reasoning="Time series column detected against numeric variable",
                        chart_spec=spec
                    ))

        # Rule 2: Categorical Bar Chart Recommendations
        for x_col in x_candidates[:3]:
            if len(recommendations) >= 4:
                break
            for num_col in num_cols:
                if len(recommendations) >= 4:
                    break
                if x_col == num_col:
                    continue

                clean_x = sanitize_key(x_col)
                clean_y = sanitize_key(num_col)
                if clean_x == clean_y:
                    clean_y = f"{clean_y} (val)"

                grouped = {}
                counts = {}
                for x_val, n_val in zip(col_data[x_col], col_data[num_col]):
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

                    spec = ChartSpec(type="bar", title=f"Average {clean_y} by {clean_x}", x_key=clean_x, y_key=clean_y, data=chart_data)
                    recommendations.append(ChartRecommendation(
                        chart_type="bar",
                        title=f"Average {clean_y} by {clean_x}",
                        x_key=clean_x,
                        y_key=clean_y,
                        score=0.85,
                        reasoning="Low cardinality categorical column paired with numeric measure",
                        chart_spec=spec
                    ))

        # Rule 3: Row Index Fallback Line Chart
        if not recommendations and num_cols:
            num_col = num_cols[0]
            clean_y = sanitize_key(num_col)
            chart_data = []
            for idx, val in enumerate(col_data[num_col][:100]):
                if val is not None:
                    try:
                        chart_data.append({"Row Index": idx + 1, clean_y: float(str(val).replace("$", "").replace(",", ""))})
                    except (ValueError, TypeError):
                        pass

            if chart_data:
                spec = ChartSpec(type="line", title=f"{clean_y} Values by Row Index", x_key="Row Index", y_key=clean_y, data=chart_data)
                recommendations.append(ChartRecommendation(
                    chart_type="line",
                    title=f"{clean_y} Values by Row Index",
                    x_key="Row Index",
                    y_key=clean_y,
                    score=0.50,
                    reasoning="Row index fallback for numeric column",
                    chart_spec=spec
                ))

        return recommendations
