import os
import io
import re
import logging
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

def _read_csv_smart(filepath_or_buffer):
    """Reads a CSV file with automatic delimiter detection (comma, semicolon, tab, pipe)."""
    try:
        if isinstance(filepath_or_buffer, io.BytesIO):
            filepath_or_buffer.seek(0)
            df = pd.read_csv(filepath_or_buffer)
        else:
            df = pd.read_csv(filepath_or_buffer)

        # Detect non-comma delimiters (e.g. semicolon in UCI student-mat.csv, tab, pipe)
        if len(df.columns) == 1:
            col_name = str(df.columns[0])
            for sep_char in [";", "\t", "|"]:
                if sep_char in col_name:
                    if isinstance(filepath_or_buffer, io.BytesIO):
                        filepath_or_buffer.seek(0)
                        df = pd.read_csv(filepath_or_buffer, sep=sep_char)
                    else:
                        df = pd.read_csv(filepath_or_buffer, sep=sep_char)
                    break
        return df
    except Exception as e:
        logger.warning(f"Standard pandas read_csv failed ({e}). Retrying with sep=None engine=python...")
        if isinstance(filepath_or_buffer, io.BytesIO):
            filepath_or_buffer.seek(0)
            return pd.read_csv(filepath_or_buffer, sep=None, engine="python")
        return pd.read_csv(filepath_or_buffer, sep=None, engine="python")

def process_tabular_file(file_path: str = None, file_bytes: bytes = None, filename: str = None) -> dict:
    """
    Domain-Agnostic Tabular Analysis Engine for Visualizer Dashboard.
    Profiles schema dynamically, classifies columns (Datetime, Categorical, Numeric, Identifiers),
    synthesizes visual chart matrices, and produces the unified dashboard JSON spec.
    """
    fname = filename or (os.path.basename(file_path) if file_path else "dataset.csv")

    # 1. Ingestion & Multi-Sheet Handling
    raw_sheets_dict = {}
    try:
        if file_path:
            ext = file_path.split(".")[-1].lower()
            if ext == "csv":
                df = _read_csv_smart(file_path)
                raw_sheets_dict = {"Sheet1": df}
            elif ext in ["xlsx", "xls"]:
                raw_sheets_dict = pd.read_excel(file_path, sheet_name=None)
            else:
                raise ValueError(f"Unsupported tabular extension: {ext}")
        elif file_bytes is not None and fname:
            ext = fname.split(".")[-1].lower()
            buf = io.BytesIO(file_bytes)
            if ext == "csv":
                df = _read_csv_smart(buf)
                raw_sheets_dict = {"Sheet1": df}
            elif ext in ["xlsx", "xls"]:
                raw_sheets_dict = pd.read_excel(buf, sheet_name=None)
            else:
                raise ValueError(f"Unsupported tabular extension: {ext}")
        else:
            raise ValueError("Either file_path or (file_bytes and filename) must be provided.")
    except Exception as e:
        logger.error(f"Error loading tabular file '{fname}': {e}")
        raise ValueError(f"Could not read spreadsheet file. Error: {str(e)}")

    if not raw_sheets_dict:
        raise ValueError("The provided tabular dataset is empty.")

    # 2. Process All Worksheets
    processed_sheets = []
    first_df = None
    first_sheet_name = None

    for sheet_name, sheet_df in raw_sheets_dict.items():
        if sheet_df is None or sheet_df.empty:
            continue
        dt_cols, cat_cols, num_cols, id_cols, df_proc = _profile_schema(sheet_df)
        s_charts = _synthesize_charts(df_proc, dt_cols, cat_cols, num_cols)
        s_kpis = _generate_domain_kpis(df_proc, len(df_proc), len(df_proc.columns), cat_cols, num_cols)
        
        df_disp = df_proc.fillna("")
        f_cols = [{"name": str(c), "dtype": str(df_proc[c].dtype)} for c in df_proc.columns]
        p_rows = df_disp.head(100).to_dict(orient="records")

        sheet_info = {
            "sheet_name": str(sheet_name),
            "row_count": len(df_proc),
            "col_count": len(df_proc.columns),
            "columns": f_cols,
            "preview_rows": p_rows,
            "charts": s_charts,
            "kpis": s_kpis
        }
        processed_sheets.append(sheet_info)

        if first_df is None:
            first_df = df_proc
            first_sheet_name = str(sheet_name)

    if first_df is None:
        raise ValueError("All sheets in the uploaded workbook are empty.")

    # Top-level primary sheet attributes
    datetime_cols, categorical_cols, numeric_cols, identifier_cols, df_processed = _profile_schema(first_df)
    row_count = len(df_processed)
    col_count = len(df_processed.columns)

    charts = _synthesize_charts(df_processed, datetime_cols, categorical_cols, numeric_cols)
    kpis = _generate_domain_kpis(df_processed, row_count, col_count, categorical_cols, numeric_cols)
    keywords = _generate_domain_keywords(df_processed, categorical_cols)
    exec_summary = _generate_executive_summary(fname, row_count, col_count, categorical_cols, numeric_cols, df_processed)

    df_display = df_processed.fillna("")
    formatted_cols = [{"name": str(c), "dtype": str(df_processed[c].dtype)} for c in df_processed.columns]
    preview_rows = df_display.head(100).to_dict(orient="records")
    raw_markdown = df_display.head(10).to_markdown(index=False)

    tabular_dict = {
        "row_count": row_count,
        "col_count": col_count,
        "total_rows": row_count,
        "total_columns": col_count,
        "columns": formatted_cols,
        "preview_rows": preview_rows,
        "data_preview": df_display.head(5).to_dict(orient="records"),
        "markdown_table": raw_markdown,
        "kpis": kpis,
        "charts": charts,
        "sheets": processed_sheets
    }

    return {
        "status": "success",
        "source_type": "tabular",
        "file_name": fname,
        "file_type": fname.split(".")[-1].lower(),
        "data_category": "tabular",
        "dashboard_title": f"Executive Data Summary: {fname}",
        "executive_summary": exec_summary,
        "kpis": kpis,
        "keywords": keywords,
        "charts": charts,
        "raw_markdown": raw_markdown,
        "tabular": tabular_dict,
        "tabular_summary": tabular_dict
    }

def _get_first_non_empty_sheet(sheets_dict) -> pd.DataFrame:
    """Helper to select the first non-empty sheet dataframe from an Excel file."""
    if isinstance(sheets_dict, dict):
        for name, sheet_df in sheets_dict.items():
            if not sheet_df.empty:
                return sheet_df
        return list(sheets_dict.values())[0]
    return sheets_dict

def _profile_schema(df: pd.DataFrame):
    """Classifies columns into Datetime, Categorical, Numeric, and Identifiers."""
    df_clean = df.copy()
    datetime_cols = []
    categorical_cols = []
    numeric_cols = []
    identifier_cols = []

    total_rows = len(df_clean)

    for col in df_clean.columns:
        series = df_clean[col].dropna()
        if series.empty:
            continue

        n_unique = series.nunique()
        unique_ratio = n_unique / max(total_rows, 1)

        # A. High-Cardinality / Identifiers Check (>90% unique)
        if unique_ratio > 0.90 and total_rows > 10:
            identifier_cols.append(col)

        # B. Datetime Check
        is_date = False
        if series.dtype == 'datetime64[ns]':
            is_date = True
        elif series.dtype == 'object':
            # Sample check for speed
            sample = series.head(20).astype(str)
            if sample.str.contains(r'\d{2,4}[-/.]\d{1,2}[-/.]\d{1,2}').mean() > 0.6:
                try:
                    df_clean[col] = pd.to_datetime(df_clean[col], errors='coerce')
                    is_date = True
                except Exception:
                    pass

        if is_date:
            datetime_cols.append(col)
            continue

        # C. Numeric Check
        is_numeric = False
        if pd.api.types.is_numeric_dtype(series):
            is_numeric = True
        else:
            # Try cleaning numeric strings (e.g. "$1,450", "85%")
            sample_clean = series.astype(str).str.replace(r'[$,%]', '', regex=True)
            converted = pd.to_numeric(sample_clean, errors='coerce')
            if converted.notna().mean() > 0.75:
                df_clean[col] = converted
                is_numeric = True

        if is_numeric:
            # Discrete low cardinality integers can also serve as categorical
            if n_unique < 15:
                categorical_cols.append(col)
            numeric_cols.append(col)
            continue

        # D. Categorical Check (< 20 unique OR < 5% of row count)
        if not is_numeric and not is_date:
            if n_unique < 30 or unique_ratio < 0.15:
                categorical_cols.append(col)

    return datetime_cols, categorical_cols, numeric_cols, identifier_cols, df_clean

def _synthesize_charts(df: pd.DataFrame, datetime_cols: list, categorical_cols: list, numeric_cols: list) -> list:
    """Synthesizes max 4 visual chart specs applying aggregation rules."""
    charts = []

    # Rule 1: 1 Categorical + 1 Numeric (Bar Chart top 10 categories)
    if categorical_cols and numeric_cols:
        cat_col = categorical_cols[0]
        num_col = numeric_cols[0]
        try:
            grouped = df.groupby(cat_col)[num_col].sum().reset_index()
            grouped[num_col] = grouped[num_col].round(2)
            top10 = grouped.nlargest(10, num_col)
            
            x_vals = top10[cat_col].astype(str).tolist()
            y_vals = [float(v) for v in top10[num_col].tolist()]

            if len(x_vals) > 0:
                charts.append({
                    "title": f"Top {len(x_vals)} {cat_col} by Total {num_col}",
                    "chart_type": "bar",
                    "x_axis_label": str(cat_col),
                    "y_axis_label": str(num_col),
                    "x_data": x_vals,
                    "y_data": y_vals
                })
        except Exception as e:
            logger.debug(f"Error synthesizing Bar Chart: {e}")

    # Rule 2: 1 Categorical Frequency Distribution (Pie Chart top 6)
    if categorical_cols:
        cat_col = categorical_cols[0]
        try:
            counts = df[cat_col].value_counts().head(6).reset_index()
            counts.columns = [cat_col, "count"]
            x_vals = counts[cat_col].astype(str).tolist()
            y_vals = [int(v) for v in counts["count"].tolist()]

            if len(x_vals) > 0:
                charts.append({
                    "title": f"Distribution of {cat_col}",
                    "chart_type": "pie",
                    "x_axis_label": str(cat_col),
                    "y_axis_label": "Frequency",
                    "x_data": x_vals,
                    "y_data": y_vals
                })
        except Exception as e:
            logger.debug(f"Error synthesizing Pie Chart: {e}")

    # Rule 3: 1 Datetime + 1 Numeric (Line Chart time-series)
    if datetime_cols and numeric_cols:
        date_col = datetime_cols[0]
        num_col = numeric_cols[0]
        try:
            temp_df = df.dropna(subset=[date_col, num_col]).sort_values(date_col)
            temp_df['date_str'] = temp_df[date_col].dt.strftime('%Y-%m-%d')
            grouped = temp_df.groupby('date_str')[num_col].sum().reset_index().head(12)
            
            x_vals = grouped['date_str'].tolist()
            y_vals = [float(v) for v in grouped[num_col].round(2).tolist()]

            if len(x_vals) > 0:
                charts.append({
                    "title": f"{num_col} Trend Over Time",
                    "chart_type": "line",
                    "x_axis_label": "Date",
                    "y_axis_label": str(num_col),
                    "x_data": x_vals,
                    "y_data": y_vals
                })
        except Exception as e:
            logger.debug(f"Error synthesizing Line Chart: {e}")

    # Rule 4: 100% Numeric Fallback Distribution (Bar Chart of column means)
    if not charts and numeric_cols:
        try:
            means = df[numeric_cols[:6]].mean().round(2).reset_index()
            means.columns = ["metric", "mean_val"]
            x_vals = means["metric"].astype(str).tolist()
            y_vals = [float(v) for v in means["mean_val"].tolist()]

            charts.append({
                "title": "Average Metric Values Comparison",
                "chart_type": "bar",
                "x_axis_label": "Metric",
                "y_axis_label": "Average Value",
                "x_data": x_vals,
                "y_data": y_vals
            })
        except Exception as e:
            logger.debug(f"Error synthesizing Numeric Fallback Chart: {e}")

    return charts

def _generate_domain_kpis(df: pd.DataFrame, row_count: int, col_count: int, categorical_cols: list, numeric_cols: list) -> list:
    """Generates 3-5 smart domain KPI cards."""
    kpis = [
        {"label": "Total Records", "value": f"{row_count:,} Rows"},
        {"label": "Total Columns", "value": f"{col_count} Fields"}
    ]

    if numeric_cols:
        num_col = numeric_cols[0]
        total_val = df[num_col].sum()
        avg_val = df[num_col].mean()
        if not np.isnan(total_val):
            kpis.append({"label": f"Total {num_col}", "value": f"{total_val:,.2f}".rstrip('0').rstrip('.')})
        if not np.isnan(avg_val):
            kpis.append({"label": f"Average {num_col}", "value": f"{avg_val:,.2f}".rstrip('0').rstrip('.')})

    if categorical_cols:
        cat_col = categorical_cols[0]
        top_cat = df[cat_col].mode()
        if not top_cat.empty:
            kpis.append({"label": f"Dominant {cat_col}", "value": str(top_cat.iloc[0])})

    return kpis[:5]

def _generate_domain_keywords(df: pd.DataFrame, categorical_cols: list) -> list:
    """Generates keyword relevance list from column names and dominant category values."""
    keywords = []
    for col in df.columns:
        clean_word = re.sub(r"[^\w]", "", str(col)).capitalize()
        if len(clean_word) > 2:
            keywords.append({"word": clean_word, "score": 0.95})

    if categorical_cols:
        top_vals = df[categorical_cols[0]].value_counts().head(5).index.tolist()
        for val in top_vals:
            clean_val = re.sub(r"[^\w]", "", str(val)).capitalize()
            if len(clean_val) > 2 and clean_val not in [k["word"] for k in keywords]:
                keywords.append({"word": clean_val, "score": 0.85})

    return keywords[:12]

def _generate_executive_summary(fname: str, row_count: int, col_count: int, categorical_cols: list, numeric_cols: list, df: pd.DataFrame) -> str:
    """Synthesizes a 2-3 sentence executive overview of the dataset."""
    cat_str = f" categorized across '{categorical_cols[0]}'" if categorical_cols else ""
    num_str = f" with key numerical metrics tracked in '{numeric_cols[0]}'" if numeric_cols else ""
    
    return f"Dataset '{fname}' contains {row_count:,} rows and {col_count} columns{cat_str}. Key metrics have been processed to highlight dominant category distributions{num_str}. The dataset is clean and indexed for dynamic dashboard reporting."
