from pydantic import BaseModel, Field
from typing import List, Optional

class ExtractedMetric(BaseModel):
    category: str = Field(description="Name or grouping category of the metric")
    metric_value: float = Field(description="Numerical value extracted from text or table")
    unit: Optional[str] = Field(default=None, description="Unit of measurement e.g., USD, %, kg, units")
    context_snippet: str = Field(description="Exact phrase/sentence supporting this metric")
    page_number: Optional[int] = Field(default=1, description="Source page number where metric appears")
    bbox: Optional[List[float]] = Field(default=None, description="Spatial bounding box coordinates [x0, y0, x1, y1]")

class KeyValuePair(BaseModel):
    key_name: str = Field(description="Attribute or label name extracted from text")
    value: str = Field(description="Textual or code value corresponding to key_name")
    context_snippet: str = Field(description="Supporting sentence or paragraph snippet")
    page_number: Optional[int] = Field(default=1, description="Source page number")

class ExtractedTable(BaseModel):
    table_title: Optional[str] = Field(default="Extracted Table", description="Title or header of table")
    headers: List[str] = Field(default_factory=list, description="Column names")
    rows: List[List[Optional[str]]] = Field(default_factory=list, description="2D cell data rows")
    context_snippet: Optional[str] = Field(default="", description="Surrounding table text context")
    page_number: Optional[int] = Field(default=1, description="Source page number")

class DocumentAnalytics(BaseModel):
    document_title: str = Field(default="Untitled Document", description="Extracted document title")
    report_date: Optional[str] = Field(default=None, description="Extracted document date")
    summary: Optional[str] = Field(default="", description="Executive summary of document")
    keywords: List[str] = Field(default_factory=list, description="Key topics and words")
    metrics: List[ExtractedMetric] = Field(default_factory=list, description="All numerical metrics")
    key_value_pairs: List[KeyValuePair] = Field(default_factory=list, description="Extracted key-value facts")
    tables: List[ExtractedTable] = Field(default_factory=list, description="Extracted table grids")
