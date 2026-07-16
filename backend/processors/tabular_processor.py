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
    
    # 3. Preview Rows (first 100)
    # Serialize datetimes for JSON
    preview_rows = []
    for row in rows[:100]:
        clean_row = []
        for val in row:
            if isinstance(val, datetime):
                clean_row.append(val.isoformat())
            else:
                clean_row.append(val)
        preview_rows.append(clean_row)

    # 4. Summaries
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

    # 5. Simple Autogen Charts
    charts = []
    cat_cols = list(categorical_summary.keys())
    num_cols = list(numeric_summary.keys())
    
    if cat_cols and num_cols:
        x_col = cat_cols[0]
        y_col = num_cols[0]
        
        # Group by x_col, average y_col
        grouped = {}
        counts = {}
        for x_val, y_val in zip(col_data[x_col], col_data[y_col]):
            if x_val is not None and isinstance(y_val, (int, float)):
                x_str = str(x_val)
                grouped[x_str] = grouped.get(x_str, 0.0) + float(y_val)
                counts[x_str] = counts.get(x_str, 0) + 1
                
        # Calculate averages
        averages = {k: grouped[k]/counts[k] for k in grouped}
        
        # Get top 5 by average
        top_averages = sorted(averages.items(), key=lambda item: item[1], reverse=True)[:5]
        
        chart_data = []
        for k, v in top_averages:
            chart_data.append({x_col: k, y_col: v})
            
        charts.append(ChartData(
            type="bar",
            title=f"Average {y_col} by {x_col}",
            x_key=x_col,
            y_key=y_col,
            data=chart_data
        ))

    return TabularResult(
        columns=columns,
        preview_rows=preview_rows,
        row_count=row_count,
        col_count=col_count,
        numeric_summary=numeric_summary,
        categorical_summary=categorical_summary,
        charts=charts
    )
