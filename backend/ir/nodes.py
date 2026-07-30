# ==============================================================================
# CANONICAL IR NODES (DEPRECATED & COMMENTED OUT FOR MISTRAL OCR)
# All original lines preserved below as comments.
# ==============================================================================
# from pydantic import BaseModel, Field
# from uuid import UUID, uuid4
# from typing import Optional, List, Dict, Any
# from ir.confidence import ConfidenceObject
# from ir.provenance import ProvenanceRecord
# 
# class IRNode(BaseModel):
#     """Abstract base node for Canonical Document IR AST graph."""
#     node_id: UUID = Field(default_factory=uuid4)
#     node_type: str  # "header", "paragraph", "table", "cell", "image", "list"
#     page_number: Optional[int] = Field(default=1)
#     bbox: Optional[List[float]] = Field(default=None, description="Spatial bounding box [x0, y0, x1, y1]")
#     confidence: ConfidenceObject = Field(default_factory=ConfidenceObject)
#     metadata: Dict[str, Any] = Field(default_factory=dict)
# 
# class HeaderNode(IRNode):
#     """Header / Heading section node."""
#     node_type: str = "header"
#     level: int = Field(default=1, ge=1, le=6)
#     text: str
# 
# class ParagraphNode(IRNode):
#     """Paragraph text node."""
#     node_type: str = "paragraph"
#     text: str
# 
# class CellNode(BaseModel):
#     """Individual table cell within a TableNode matrix."""
#     cell_id: UUID = Field(default_factory=uuid4)
#     row_index: int
#     col_index: int
#     raw_text: str
#     value: Any = None
#     data_type: str = "string"  # "string", "number", "date", "boolean"
#     bbox: Optional[List[float]] = None
#     confidence: ConfidenceObject = Field(default_factory=ConfidenceObject)
# 
# class TableNode(IRNode):
#     """2D tabular grid node storing structured matrices with zero-copy cell views."""
#     node_type: str = "table"
#     table_title: Optional[str] = None
#     headers: List[str] = Field(default_factory=list)
#     rows: List[List[Any]] = Field(default_factory=list)
#     cell_matrix: List[List[CellNode]] = Field(default_factory=list)
#     row_count: int = 0
#     col_count: int = 0
# 
# class ImageNode(IRNode):
#     """Embedded image / visual figure node."""
#     node_type: str = "image"
#     image_id: str
#     caption: Optional[str] = None
#     ocr_text: Optional[str] = None
# 
# class ListNode(IRNode):
#     """Ordered or unordered list node."""
#     node_type: str = "list"
#     is_ordered: bool = False
#     items: List[str] = Field(default_factory=list)

class IRNode:
    pass
class HeaderNode:
    pass
class ParagraphNode:
    pass
class CellNode:
    pass
class TableNode:
    pass
class ImageNode:
    pass
class ListNode:
    pass
