import time
import hashlib
import logging
from typing import Optional, Dict, Any

from context.pipeline_context import PipelineContext
from parsers.factory import get_parser_factory
from processors.normalizer import DocumentNormalizer
from processors.enricher import DocumentEnricher
from processors.profiler import DataProfiler
from processors.recommender import VisualizationRecommender
from services.dashboard_builder import DashboardBuilder
from models.schemas import UploadResponse
from engine.db import get_cached_analytics, save_cached_analytics

logger = logging.getLogger(__name__)

class DocumentPipelineService:
    """Orchestrator managing document-to-dashboard pipeline context and stage execution."""

    def __init__(self):
        self.parser_factory = get_parser_factory()

    def process_document(self, file_bytes: bytes, filename: str) -> UploadResponse:
        t0 = time.perf_counter()
        file_hash = hashlib.sha256(file_bytes).hexdigest()

        context = PipelineContext(
            filename=filename,
            file_bytes=file_bytes,
            file_hash=file_hash
        )

        # Stage 1: Parser Lookup & Execution
        t_stage = time.perf_counter()
        parser = self.parser_factory.get_parser(file_bytes, filename)
        context.parser_used = parser.__class__.__name__
        context.content = parser.parse(file_bytes, filename)
        context.record_stage_time("parse", (time.perf_counter() - t_stage) * 1000)

        # Stage 2: Normalization
        t_stage = time.perf_counter()
        raw_ext = filename.split(".")[-1] if "." in filename else "txt"
        context.model = DocumentNormalizer.normalize(context.content, filename, raw_ext)
        context.record_stage_time("normalize", (time.perf_counter() - t_stage) * 1000)

        # Stage 3: Post-Parsing Enrichment
        t_stage = time.perf_counter()
        context.model = DocumentEnricher.enrich(context.model)
        context.record_stage_time("enrich", (time.perf_counter() - t_stage) * 1000)

        # Stage 4: Data Profiling
        t_stage = time.perf_counter()
        context.profile = DataProfiler.profile(context.model)
        context.record_stage_time("profile", (time.perf_counter() - t_stage) * 1000)

        # Stage 5: Chart Recommendation
        t_stage = time.perf_counter()
        context.recommendations = VisualizationRecommender.recommend(context.profile, context.model)
        context.record_stage_time("recommend", (time.perf_counter() - t_stage) * 1000)

        # Stage 5.5: Document Analytics & Traceability Bounding Box Extraction
        analytics_data = None
        if context.model.data_category != "tabular":
            t_stage = time.perf_counter()
        try:
            from engine.document_extractor import create_heuristic_fallback_analytics, merge_native_and_vision_data, save_document_analytics
            raw_analytics = create_heuristic_fallback_analytics(filename, context.model.raw_text)
            
            # Merge summary and keywords from profile if present
            if context.profile:
                if context.profile.summary:
                    raw_analytics.summary = context.profile.summary
                if context.profile.keywords:
                    raw_analytics.keywords = [k.word if hasattr(k, "word") else str(k) for k in context.profile.keywords]

            # Match spatial bounding boxes if page blocks are available
            if context.content and context.content.blocks_by_page:
                merged = merge_native_and_vision_data(
                    {"blocks_by_page": context.content.blocks_by_page, "text": context.model.raw_text},
                    raw_analytics,
                    filename
                )
                analytics_data = merged.get("analytics")
            else:
                analytics_data = raw_analytics

            # Persist analytics to DuckDB for metrics API endpoints
            try:
                if hasattr(analytics_data, "metrics"):
                    save_document_analytics(filename, analytics_data)
            except Exception as db_err:
                logger.warning(f"DuckDB save error: {db_err}")

        except Exception as analytics_err:
            logger.warning(f"Analytics extraction error for '{filename}': {analytics_err}")
        context.record_stage_time("analytics", (time.perf_counter() - t_stage) * 1000)

        # Stage 6: Dashboard Response Construction via Exporter
        # Stage 6: Dashboard Response Export
        t_stage = time.perf_counter()
        elapsed_total = time.perf_counter() - t0
        from services.dashboard_builder import DashboardBuilder
        response = DashboardBuilder.build_response(
            model=context.model,
            profile=context.profile,
            recommendations=context.recommendations,
            analytics=analytics_data,
            processing_time=elapsed_total
        )
        context.record_stage_time("build_response", (time.perf_counter() - t_stage) * 1000)
        context.response = response

        return response

# Default pipeline service instance
_default_pipeline_service = DocumentPipelineService()

def get_pipeline_service() -> DocumentPipelineService:
    return _default_pipeline_service
