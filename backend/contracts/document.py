from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class TableData(BaseModel):
    """Clean 2D matrix structure representing an extracted table grid."""
    table_title: Optional[str] = Field(default="Table Grid", description="Table title or section header")
    headers: List[str] = Field(default_factory=list, description="Column header names")
    rows: List[List[Any]] = Field(default_factory=list, description="2D cell matrix rows")
    page_number: Optional[int] = Field(default=1, description="Page number where table originates")
    context_snippet: Optional[str] = Field(default="", description="Surrounding text context")

@dataclass
class DocumentContent:
    """Raw content contract returned by individual parser adapters before normalization."""
    raw_text: str = ""
    tables: List[TableData] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    page_count: Optional[int] = None
    paragraph_count: Optional[int] = None
    structured_tsv: Optional[str] = None
    blocks_by_page: Dict[int, Any] = field(default_factory=dict)
    file_bytes: Optional[bytes] = None

class UnifiedDocumentModel(BaseModel):
    """Standardized document contract shared across all downstream profiling & enrichment stages."""
    filename: str
    file_type: str
    data_category: str = "text"  # "tabular", "text", "mixed", "qualitative_document"
    tables: List[TableData] = Field(default_factory=list)
    raw_text: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)
    blocks_by_page: Dict[int, Any] = Field(default_factory=dict)
    page_count: Optional[int] = 1
    paragraph_count: Optional[int] = None
    word_count: int = 0
