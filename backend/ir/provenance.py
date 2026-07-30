# ==============================================================================
# CANONICAL IR PROVENANCE (DEPRECATED & COMMENTED OUT FOR MISTRAL OCR)
# All original lines preserved below as comments.
# ==============================================================================
# from pydantic import BaseModel, Field
# from datetime import datetime
# from typing import Optional, List, Dict, Any
# 
# class ProvenanceStep(BaseModel):
#     """Single processing step step tracking processor version and execution latency."""
#     stage_name: str  # "parse", "ocr", "enrichment", "llm_summary"
#     processor_name: str  # "PyMuPDFAdapter", "RapidOCR_v4", "NVIDIA_LLaMA_3.1"
#     version: str = Field(default="1.0.0")
#     execution_time_ms: float = 0.0
#     timestamp: datetime = Field(default_factory=datetime.utcnow)
#     parameters: Dict[str, Any] = Field(default_factory=dict)
# 
# class ProvenanceRecord(BaseModel):
#     """Complete provenance and ancestry history for a document or IR node."""
#     created_by: str  # Component ID or parser name
#     source_filename: str
#     source_hash_sha256: str = ""
#     created_at: datetime = Field(default_factory=datetime.utcnow)
#     steps: List[ProvenanceStep] = Field(default_factory=list)

class ProvenanceStep:
    pass
class ProvenanceRecord:
    pass
