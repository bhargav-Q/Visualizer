# ==============================================================================
# CANONICAL IR CONFIDENCE (DEPRECATED & COMMENTED OUT FOR MISTRAL OCR)
# All original lines preserved below as comments.
# ==============================================================================
# from pydantic import BaseModel, Field
# from typing import Optional, List, Dict, Any
# 
# class ConfidenceFactors(BaseModel):
#     """Multi-factored granular scoring factors explaining confidence origins."""
#     ocr_confidence: Optional[float] = Field(default=1.0, description="RapidOCR detection score [0.0-1.0]")
#     alignment_score: Optional[float] = Field(default=1.0, description="Spatial grid row/column alignment score")
#     llm_validation: Optional[float] = Field(default=1.0, description="LLM JSON schema parsing score")
#     type_coercion_score: Optional[float] = Field(default=1.0, description="Numeric/date parsing confidence")
# 
# class ConfidenceObject(BaseModel):
#     """Multi-factored confidence model attached to document nodes and extracted elements."""
#     score: float = Field(default=1.0, description="Overall aggregate confidence score [0.0 - 1.0]")
#     level: str = Field(default="HIGH", description="Confidence tier: HIGH (>=0.85), MEDIUM (0.60-0.84), LOW (<0.60)")
#     extraction_method: str = Field(default="native_digital", description="Method: pymupdf_digital, rapidocr, vision_vlm, llm_table")
#     factors: ConfidenceFactors = Field(default_factory=ConfidenceFactors)
#     validation_status: str = Field(default="VALIDATED", description="Status: VALIDATED, UNVERIFIED, CONFLICT")
#     explanation: str = Field(default="Extracted directly from native document text streams.")
#     warnings: List[str] = Field(default_factory=list)
# 
# class ElementConfidenceMap(BaseModel):
#     """Aggregated confidence mapping across document hierarchy levels."""
#     document_confidence: ConfidenceObject = Field(default_factory=ConfidenceObject)
#     page_confidence: Dict[int, ConfidenceObject] = Field(default_factory=dict)
#     element_confidence: Dict[str, ConfidenceObject] = Field(default_factory=dict)

class ConfidenceFactors:
    pass
class ConfidenceObject:
    pass
class ElementConfidenceMap:
    pass
