import re
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Any

class ExtractedMetric(BaseModel):
    category: str = Field(default="General Metric", description="Name or grouping category of the metric")
    metric_value: float = Field(default=0.0, description="Numerical value extracted from text or table")
    unit: Optional[str] = Field(default=None, description="Unit of measurement e.g., USD, %, kg, units")
    context_snippet: str = Field(default="", description="Exact phrase/sentence supporting this metric")
    page_number: Optional[int] = Field(default=1, description="Source page number where metric appears")
    bbox: Optional[List[float]] = Field(default=None, description="Spatial bounding box coordinates [x0, y0, x1, y1]")
    page_width: Optional[float] = Field(default=None, description="Standard page width in points")
    page_height: Optional[float] = Field(default=None, description="Standard page height in points")

    @field_validator("category", "context_snippet", mode="before")
    @classmethod
    def parse_str_fields(cls, v: Any) -> str:
        if v is None:
            return ""
        return str(v)

    @field_validator("metric_value", mode="before")
    @classmethod
    def parse_metric_value(cls, v: Any) -> float:
        """Coerces raw values, strings, and currency text into clean floating-point numbers."""
        if v is None:
            return 0.0
        if isinstance(v, (int, float)):
            return float(v)
        if isinstance(v, str):
            cleaned = re.sub(r'[^\d.-]', '', v.replace(',', ''))
            try:
                return float(cleaned) if cleaned and cleaned != '-' else 0.0
            except ValueError:
                return 0.0
        return 0.0

class KeyValuePair(BaseModel):
    key_name: str = Field(default="Attribute", description="Attribute or label name extracted from text")
    value: str = Field(default="", description="Textual or code value corresponding to key_name")
    context_snippet: str = Field(default="", description="Supporting sentence or paragraph snippet")
    page_number: Optional[int] = Field(default=1, description="Source page number")

    @field_validator("key_name", "value", "context_snippet", mode="before")
    @classmethod
    def parse_str_fields(cls, v: Any) -> str:
        """Coerces integers, floats, or objects into clean strings."""
        if v is None:
            return ""
        return str(v)

class ExtractedTable(BaseModel):
    table_title: Optional[str] = Field(default="Extracted Table", description="Title or header of table")
    headers: List[str] = Field(default_factory=list, description="Column names")
    rows: List[List[str]] = Field(default_factory=list, description="2D cell data rows")
    context_snippet: Optional[str] = Field(default="", description="Surrounding table text context")
    page_number: Optional[int] = Field(default=1, description="Source page number")

    @field_validator("headers", mode="before")
    @classmethod
    def parse_headers(cls, v: Any) -> List[str]:
        if not isinstance(v, list):
            return []
        return [str(h) if h is not None else "" for h in v]

    @field_validator("rows", mode="before")
    @classmethod
    def parse_rows(cls, v: Any) -> List[List[str]]:
        """Converts numbers, floats, and null matrix elements into clean string cells."""
        if not isinstance(v, list):
            return []
        clean_matrix = []
        for row in v:
            if isinstance(row, list):
                clean_row = [str(cell) if cell is not None else "" for cell in row]
                clean_matrix.append(clean_row)
        return clean_matrix

class DocumentAnalytics(BaseModel):
    document_title: str = Field(default="Untitled Document", description="Extracted document title")
    report_date: Optional[str] = Field(default=None, description="Extracted document date")
    summary: Optional[str] = Field(default="", description="Executive summary of document")
    keywords: List[str] = Field(default_factory=list, description="Key topics and words")
    metrics: List[ExtractedMetric] = Field(default_factory=list, description="All numerical metrics")
    key_value_pairs: List[KeyValuePair] = Field(default_factory=list, description="Extracted key-value facts")
    tables: List[ExtractedTable] = Field(default_factory=list, description="Extracted table grids")

    @field_validator("document_title", "summary", mode="before")
    @classmethod
    def parse_str_fields(cls, v: Any) -> str:
        if v is None:
            return ""
        return str(v)

    @field_validator("keywords", mode="before")
    @classmethod
    def parse_keywords(cls, v: Any) -> List[str]:
        if not isinstance(v, list):
            return []
        return [str(kw) for kw in v if kw is not None]
