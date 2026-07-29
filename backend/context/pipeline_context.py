import time
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from contracts.document import DocumentContent, UnifiedDocumentModel
from contracts.profile import DocumentProfile
from contracts.charts import ChartRecommendation
from models.schemas import UploadResponse

@dataclass
class PipelineContext:
    """Execution context state and telemetry tracker across all pipeline stages."""
    filename: str
    file_bytes: bytes
    file_hash: str = ""
    mime_type: Optional[str] = None
    file_type: str = ""
    
    # State Artifacts across Pipeline Stages
    content: Optional[DocumentContent] = None
    model: Optional[UnifiedDocumentModel] = None
    canonical_ir: Optional[Any] = None
    profile: Optional[DocumentProfile] = None
    recommendations: List[ChartRecommendation] = field(default_factory=list)
    response: Optional[UploadResponse] = None
    
    # Telemetry and Execution Metadata
    parser_used: Optional[str] = None
    enrichments_applied: List[str] = field(default_factory=list)
    is_cached: bool = False
    stage_timings_ms: Dict[str, float] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    start_time: float = field(default_factory=time.perf_counter)

    def record_stage_time(self, stage_name: str, duration_ms: float):
        """Records execution timing for a pipeline stage."""
        self.stage_timings_ms[stage_name] = round(duration_ms, 2)

    def add_warning(self, msg: str):
        self.warnings.append(msg)

    def add_error(self, msg: str):
        self.errors.append(msg)

    @property
    def total_elapsed_ms(self) -> float:
        return round((time.perf_counter() - self.start_time) * 1000, 2)
