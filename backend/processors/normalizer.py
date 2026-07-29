import logging
from typing import Optional
from contracts.document import DocumentContent, UnifiedDocumentModel, TableData
from constants import QUANTITATIVE_SIGNALS

logger = logging.getLogger(__name__)

class DocumentNormalizer:
    """Transforms heterogeneous raw DocumentContent outputs into a normalized UnifiedDocumentModel contract."""

    @staticmethod
    def normalize(content: DocumentContent, filename: str, file_type: str) -> UnifiedDocumentModel:
        raw_text = content.raw_text or ""
        word_count = len(raw_text.split()) if raw_text else 0
        tables = content.tables or []

        # Automatic Data Category Triage
        data_category = "text"
        has_tables = len(tables) > 0 and any(len(t.rows) > 0 for t in tables)

        if has_tables and word_count < 100:
            data_category = "tabular"
        elif has_tables and word_count >= 100:
            data_category = "mixed"
        else:
            has_quant_signals = any(sig in raw_text.lower() for sig in QUANTITATIVE_SIGNALS)
            if not has_quant_signals and word_count > 30:
                data_category = "qualitative_document"

        # Sanitize Table Grids
        clean_tables = []
        for tbl in tables:
            headers = [str(h).strip() if h is not None else f"Column_{idx+1}" for idx, h in enumerate(tbl.headers)]
            clean_rows = []
            for row in tbl.rows:
                if row and any(cell is not None and str(cell).strip() != "" for cell in row):
                    clean_rows.append(list(row))
            clean_tables.append(TableData(
                table_title=tbl.table_title or filename,
                headers=headers,
                rows=clean_rows,
                page_number=tbl.page_number or 1,
                context_snippet=tbl.context_snippet or ""
            ))

        return UnifiedDocumentModel(
            filename=filename,
            file_type=file_type.lstrip("."),
            data_category=data_category,
            tables=clean_tables,
            raw_text=raw_text,
            metadata=content.metadata or {},
            blocks_by_page=content.blocks_by_page or {},
            page_count=content.page_count or 1,
            paragraph_count=content.paragraph_count,
            word_count=word_count
        )
