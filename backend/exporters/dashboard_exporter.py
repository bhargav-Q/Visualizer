from typing import Optional, List, Dict, Any
from exporters.base import BaseExporter
from ir.document import CanonicalDocumentIR
from services.dashboard_builder import DashboardBuilder
from models.schemas import UploadResponse

class DashboardExporter(BaseExporter):
    """
    Stateless read-only exporter translating CanonicalDocumentIR AST,
    DocumentProfile, and Visualization Recommendations into UploadResponse JSON for React frontend.
    """

    def export(
        self,
        doc_ir: CanonicalDocumentIR,
        profile: Optional[Any] = None,
        recommendations: Optional[List[Any]] = None,
        analytics: Optional[Any] = None,
        processing_time: float = 0.0,
        **kwargs
    ) -> UploadResponse:
        
        # Build standard UploadResponse using DashboardBuilder
        response = DashboardBuilder.build_response(
            model=doc_ir,  # Uses duck-typed accessors (get_tables, raw_text)
            profile=profile,
            recommendations=recommendations,
            analytics=analytics,
            processing_time=processing_time
        )
        return response
