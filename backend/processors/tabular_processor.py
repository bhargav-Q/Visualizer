from models.schemas import (
    TabularResult, ColumnInfo, NumericSummary, CategoricalSummary, ValueCount, ChartData
)

def process_dataframe(df) -> TabularResult:
    import pandas as pd
    import numpy as np
    
    # 1. Dimensions
    row_count, col_count = df.shape
    
    # 2. Columns Info
    columns = []
    for col in df.columns:
        columns.append(ColumnInfo(name=str(col), dtype=str(df[col].dtype)))
        
    # 3. Preview Rows (first 100)
    # Replace NaNs with None to make it JSON serializable
    preview_df = df.head(100).replace({np.nan: None})
    preview_rows = preview_df.values.tolist()
    
    # Ensure datetime columns are serialized to string properly
    for i, col in enumerate(df.columns):
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            for row in preview_rows:
                if row[i] is not None:
                    row[i] = row[i].isoformat()

    # 4. Summaries
    numeric_summary = {}
    categorical_summary = {}
    
    for col in df.columns:
        if pd.api.types.is_numeric_dtype(df[col]):
            numeric_summary[col] = NumericSummary(
                mean=float(df[col].mean()),
                median=float(df[col].median()),
                min=float(df[col].min()),
                max=float(df[col].max()),
                std=float(df[col].std()) if pd.notna(df[col].std()) else 0.0
            )
        elif pd.api.types.is_object_dtype(df[col]) or pd.api.types.is_string_dtype(df[col]):
            val_counts = df[col].value_counts().head(5)
            top_values = [
                ValueCount(value=str(k), count=int(v))
                for k, v in val_counts.items()
            ]
            categorical_summary[col] = CategoricalSummary(
                unique=int(df[col].nunique()),
                top_values=top_values
            )

    # 5. Simple Autogen Charts
    charts = []
    # If we have at least one categorical and one numeric, we can make a simple bar chart
    cat_cols = list(categorical_summary.keys())
    num_cols = list(numeric_summary.keys())
    
    if cat_cols and num_cols:
        x_col = cat_cols[0]
        y_col = num_cols[0]
        # Aggregate top 5 by mean
        grouped = df.groupby(x_col)[y_col].mean().nlargest(5)
        chart_data = []
        for k, v in grouped.items():
            chart_data.append({x_col: str(k), y_col: float(v)})
            
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
