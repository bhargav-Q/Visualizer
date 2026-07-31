from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any

class ColumnInfo(BaseModel):
    name: str
    dtype: str

class NumericSummary(BaseModel):
    mean: float
    median: float
    min: float
    max: float
    std: float

class ValueCount(BaseModel):
    value: str
    count: int

class CategoricalSummary(BaseModel):
    unique: int
    top_values: List[ValueCount]

class ChartData(BaseModel):
    type: str
    title: str
    x_key: str
    y_key: str
    data: List[Dict[str, Any]]
    page_range: Optional[str] = None

class SheetData(BaseModel):
    """Per-worksheet analysis data for multi-sheet Excel workbooks."""
    sheet_name: str
    columns: List[ColumnInfo] = Field(default_factory=list)
    preview_rows: List[List[Any]] = Field(default_factory=list)
    row_count: int = 0
    col_count: int = 0
    numeric_summary: Dict[str, NumericSummary] = Field(default_factory=dict)
    categorical_summary: Dict[str, CategoricalSummary] = Field(default_factory=dict)
    charts: List[ChartData] = Field(default_factory=list)

class TabularResult(BaseModel):
    columns: List[ColumnInfo]
    preview_rows: List[List[Any]]
    row_count: int
    col_count: int
    numeric_summary: Dict[str, NumericSummary]
    categorical_summary: Dict[str, CategoricalSummary]
    charts: List[ChartData]
    sheets: List[SheetData] = Field(default_factory=list)

class KeywordItem(BaseModel):
    word: str
    score: float

class TopicOutlineResponse(BaseModel):
    title: str = "Main Module"
    description: Optional[str] = ""
    subtopics: List[str] = []

class QualitativeSectionResponse(BaseModel):
    document_type: str = "Document Outline"
    main_topics: List[TopicOutlineResponse] = []
    extracted_highlights: List[str] = []

class TextResult(BaseModel):
    summary: str
    keywords: List[KeywordItem]
    word_count: int
    page_count: Optional[int] = None
    paragraph_count: Optional[int] = None
    ai_model: str
    qualitative_sections: Optional[List[QualitativeSectionResponse]] = []

class ExtractedMetricResponse(BaseModel):
    category: str
    metric_value: float
    unit: Optional[str] = None
    context_snippet: str
    page_number: Optional[int] = 1
    bbox: Optional[List[float]] = None
    page_width: Optional[float] = None
    page_height: Optional[float] = None

class KeyValuePairResponse(BaseModel):
    key_name: str
    value: str
    context_snippet: str
    page_number: Optional[int] = 1

class ExtractedTableResponse(BaseModel):
    table_title: Optional[str] = None
    headers: List[str] = []
    rows: List[List[Optional[str]]] = []
    page_number: Optional[int] = 1

class DocumentAnalyticsResponse(BaseModel):
    document_title: str
    report_date: Optional[str] = None
    summary: Optional[str] = ""
    keywords: List[str] = []
    metrics: List[ExtractedMetricResponse] = []
    key_value_pairs: List[KeyValuePairResponse] = []
    tables: List[ExtractedTableResponse] = []
    qualitative_sections: List[QualitativeSectionResponse] = []

class UploadResponse(BaseModel):
    file_name: str
    file_type: str
    data_category: str
    tabular: Optional[TabularResult] = None
    text: Optional[TextResult] = None
    analytics: Optional[DocumentAnalyticsResponse] = None
    processing_time: Optional[float] = None
