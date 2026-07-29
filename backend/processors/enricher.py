import logging
from typing import Optional
from contracts.document import UnifiedDocumentModel, TableData
from processors.ocr_processor import extract_tables_from_text, parse_tsv_grid

logger = logging.getLogger(__name__)

class DocumentEnricher:
    """Applies post-parsing enrichment passes (table grid reconstruction, TSV fallback, qualitative triage) to a UnifiedDocumentModel."""

    @staticmethod
    def enrich(model: UnifiedDocumentModel) -> UnifiedDocumentModel:
        """Enriches UnifiedDocumentModel by discovering embedded TSV or LLM tables if tables are empty."""
        if not model.tables or not any(len(t.rows) > 0 for t in model.tables):
            # Attempt TSV grid extraction first
            raw_table = parse_tsv_grid(model.raw_text)
            if not raw_table:
                raw_table = extract_tables_from_text(model.raw_text)

            if raw_table and raw_table.get("rows"):
                headers = raw_table.get("headers", [])
                rows = raw_table.get("rows", [])
                model.tables.append(TableData(
                    table_title=f"Extracted Table ({model.filename})",
                    headers=headers,
                    rows=rows,
                    page_number=1
                ))
                if model.data_category == "text":
                    model.data_category = "mixed"

        return model
