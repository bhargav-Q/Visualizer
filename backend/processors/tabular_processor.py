import statistics
from collections import Counter
from datetime import datetime
from models.schemas import (
    TabularResult, ColumnInfo, NumericSummary, CategoricalSummary, ValueCount, ChartData
)

def process_tabular_data(raw_data) -> TabularResult:
    """
    Processes raw tabular data (headers and rows) into a TabularResult using pure Python,
    completely avoiding pandas/numpy to bypass AppLocker native extension blocks.
    """
    headers = raw_data.get("headers", [])
    rows = raw_data.get("rows", [])
    
    # 1. Dimensions
    row_count = len(rows)
    col_count = len(headers)
    
    # Extract columns into lists for easier vertical processing
    col_data = {h: [] for h in headers}
    for row in rows:
        for i, h in enumerate(headers):
            val = row[i] if i < len(row) else None
            col_data[h].append(val)
            
    # Determine basic types by sampling
    col_types = {}
    for h in headers:
        data = [x for x in col_data[h] if x is not None]
        if not data:
            col_types[h] = "string"
        else:
            # Check if predominantly numeric
            numeric_count = sum(1 for x in data if isinstance(x, (int, float)))
            if numeric_count > len(data) * 0.8:
                col_types[h] = "numeric"
            elif isinstance(data[0], datetime):
                col_types[h] = "datetime"
            else:
                col_types[h] = "string"

    # 2. Columns Info
    columns = [ColumnInfo(name=str(h), dtype=col_types[h]) for h in headers]

    # 3. Summaries
    numeric_summary = {}
    categorical_summary = {}
    
    for h in headers:
        data = [x for x in col_data[h] if x is not None]
        if not data:
            continue
            
        if col_types[h] == "numeric":
            try:
                # Ensure all are castable to float
                num_data = [float(x) for x in data if isinstance(x, (int, float))]
                if num_data:
                    numeric_summary[h] = NumericSummary(
                        mean=statistics.mean(num_data),
                        median=statistics.median(num_data),
                        min=min(num_data),
                        max=max(num_data),
                        std=statistics.stdev(num_data) if len(num_data) > 1 else 0.0
                    )
            except Exception:
                pass # Fallback to categorical if math fails
                
        if h not in numeric_summary: # Treat as categorical
            str_data = [str(x) for x in data]
            counts = Counter(str_data)
            top_values = [
                ValueCount(value=k, count=v)
                for k, v in counts.most_common(5)
            ]
            categorical_summary[h] = CategoricalSummary(
                unique=len(counts),
                top_values=top_values
            )

    # 5. Smart Autogen Charts (Up to 4)
    charts = []
    num_cols = list(numeric_summary.keys())
    date_cols = [h for h in headers if col_types[h] == "datetime"]
    
    # Filter for low-cardinality categorical columns (between 2 and 20 unique values)
    # Exclude identifier columns that scale with row count (only if row count is substantial)
    cat_cols = [
        h for h, summary in categorical_summary.items()
        if 2 <= summary.unique <= 20 and (row_count <= 10 or summary.unique < row_count * 0.9)
    ]
    # Sort categorical columns by unique counts (cleaner/simpler charts first)
    cat_cols.sort(key=lambda h: categorical_summary[h].unique)

    # A. Time Series Line Charts (Up to 2)
    line_charts_count = 0
    for date_col in date_cols:
        if line_charts_count >= 2:
            break
        for num_col in num_cols:
            if line_charts_count >= 2:
                break
            
            # Group by year-month
            grouped = {}
            for d_val, n_val in zip(col_data[date_col], col_data[num_col]):
                if isinstance(d_val, datetime) and n_val is not None and isinstance(n_val, (int, float)):
                    month_str = d_val.strftime("%Y-%m")
                    grouped[month_str] = grouped.get(month_str, 0.0) + float(n_val)
            
            if grouped:
                sorted_months = sorted(grouped.keys())
                chart_data = [{date_col: m, num_col: grouped[m]} for m in sorted_months]
                
                charts.append(ChartData(
                    type="line",
                    title=f"Total {num_col} over Time",
                    x_key=date_col,
                    y_key=num_col,
                    data=chart_data
                ))
                line_charts_count += 1

    # B. Categorical Bar Charts (Up to remainder to make 4)
    bar_charts_count = 0
    max_bar_charts = max(0, 4 - len(charts))
    for cat_col in cat_cols:
        if bar_charts_count >= max_bar_charts:
            break
        for num_col in num_cols:
            if bar_charts_count >= max_bar_charts:
                break
            
            # Group by category, compute average
            grouped = {}
            counts = {}
            for c_val, n_val in zip(col_data[cat_col], col_data[num_col]):
                if c_val is not None and n_val is not None and isinstance(n_val, (int, float)):
                    c_str = str(c_val)
                    grouped[c_str] = grouped.get(c_str, 0.0) + float(n_val)
                    counts[c_str] = counts.get(c_str, 0) + 1
            
            if grouped:
                # Calculate averages
                averages = {k: grouped[k] / counts[k] for k in grouped}
                sorted_categories = sorted(averages.items(), key=lambda item: item[1], reverse=True)
                
                chart_data = [{cat_col: k, num_col: v} for k, v in sorted_categories]
                
                charts.append(ChartData(
                    type="bar",
                    title=f"Average {num_col} by {cat_col}",
                    x_key=cat_col,
                    y_key=num_col,
                    data=chart_data
                ))
                bar_charts_count += 1

    return TabularResult(
        columns=columns,
        row_count=row_count,
        col_count=col_count,
        numeric_summary=numeric_summary,
        categorical_summary=categorical_summary,
        charts=charts
    )
