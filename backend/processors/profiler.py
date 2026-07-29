import statistics
from collections import Counter
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional

from contracts.document import UnifiedDocumentModel, TableData
from contracts.profile import DocumentProfile, ColumnProfile
from models.schemas import NumericSummary, CategoricalSummary, ValueCount
from processors.text_processor import generate_local_fallback_text_result

class DataProfiler:
    """Computes statistical metrics, data distributions, and keyword rankings from a UnifiedDocumentModel."""

    @staticmethod
    def _profile_single_table(table: TableData) -> Tuple[
        List[ColumnProfile],
        Dict[str, NumericSummary],
        Dict[str, CategoricalSummary],
        int, int
    ]:
        """Profile a single table and return (columns, numeric_summaries, categorical_summaries, row_count, col_count)."""
        headers = table.headers
        rows = table.rows
        row_count = len(rows)
        col_count = len(headers)

        col_data = {h: [] for h in headers}
        for row in rows:
            for i, h in enumerate(headers):
                val = row[i] if i < len(row) else None
                if isinstance(val, str):
                    clean_val = val.replace("$", "").replace(",", "").replace("%", "").strip()
                    try:
                        val = float(clean_val) if "." in clean_val else int(clean_val)
                    except ValueError:
                        pass
                col_data[h].append(val)

        columns: List[ColumnProfile] = []
        numeric_summaries: Dict[str, NumericSummary] = {}
        categorical_summaries: Dict[str, CategoricalSummary] = {}

        for h in headers:
            data = [x for x in col_data[h] if x is not None]
            missing_count = row_count - len(data)

            if not data:
                columns.append(ColumnProfile(name=h, dtype="string", missing_count=missing_count, unique_count=0))
                continue

            num_count = sum(1 for x in data if isinstance(x, (int, float)))
            if num_count >= len(data) * 0.5:
                dtype = "numeric"
                num_data = [float(x) for x in data if isinstance(x, (int, float))]
                if num_data:
                    numeric_summaries[h] = NumericSummary(
                        mean=statistics.mean(num_data),
                        median=statistics.median(num_data),
                        min=min(num_data),
                        max=max(num_data),
                        std=statistics.stdev(num_data) if len(num_data) > 1 else 0.0
                    )
            elif isinstance(data[0], datetime):
                dtype = "datetime"
            else:
                dtype = "string"

            unique_set = set(str(x) for x in data)
            is_discrete = (2 <= len(unique_set) <= 30)

            if h not in numeric_summaries:
                str_data = [str(x) for x in data]
                counts = Counter(str_data)
                top_vals = [ValueCount(value=k, count=v) for k, v in counts.most_common(5)]
                categorical_summaries[h] = CategoricalSummary(
                    unique=len(counts),
                    top_values=top_vals
                )

            columns.append(ColumnProfile(
                name=h,
                dtype=dtype,
                missing_count=missing_count,
                unique_count=len(unique_set),
                is_discrete=is_discrete
            ))

        return columns, numeric_summaries, categorical_summaries, row_count, col_count

    @staticmethod
    def profile(model: UnifiedDocumentModel) -> DocumentProfile:
        filename = model.filename
        file_type = model.file_type
        data_category = model.data_category

        # Default text profiling
        text_res = generate_local_fallback_text_result(
            raw_text=model.raw_text,
            page_count=model.page_count,
            paragraph_count=model.paragraph_count
        )

        if not model.tables or not model.tables[0].rows:
            return DocumentProfile(
                filename=filename,
                file_type=file_type,
                data_category=data_category,
                word_count=model.word_count,
                summary=text_res.summary,
                keywords=text_res.keywords,
                metadata=model.metadata
            )

        # Profile the primary table (first sheet — backward compatible)
        primary_table = model.tables[0]
        columns, numeric_summaries, categorical_summaries, row_count, col_count = \
            DataProfiler._profile_single_table(primary_table)

        # Profile additional sheets if present
        sheet_profiles = []
        if len(model.tables) > 1:
            for tbl in model.tables:
                s_cols, s_num, s_cat, s_rows, s_colcount = DataProfiler._profile_single_table(tbl)
                sheet_name = (tbl.table_title or "Sheet").replace("Sheet: ", "")
                sheet_profiles.append({
                    "sheet_name": sheet_name,
                    "columns": s_cols,
                    "numeric_summaries": s_num,
                    "categorical_summaries": s_cat,
                    "row_count": s_rows,
                    "col_count": s_colcount,
                    "rows": tbl.rows,
                    "headers": tbl.headers
                })

        profile = DocumentProfile(
            filename=filename,
            file_type=file_type,
            data_category=data_category,
            row_count=row_count,
            col_count=col_count,
            columns=columns,
            numeric_summaries=numeric_summaries,
            categorical_summaries=categorical_summaries,
            word_count=model.word_count,
            summary=text_res.summary,
            keywords=text_res.keywords,
            metadata=model.metadata
        )

        # Attach sheet profiles as extra metadata for downstream consumers
        if sheet_profiles:
            profile.metadata = profile.metadata or {}
            profile.metadata["sheet_profiles"] = sheet_profiles

        return profile
