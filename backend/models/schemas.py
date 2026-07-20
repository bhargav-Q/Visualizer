from pydantic import BaseModel
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

class TabularResult(BaseModel):
    columns: List[ColumnInfo]
    preview_rows: List[List[Any]]
    row_count: int
    col_count: int
    numeric_summary: Dict[str, NumericSummary]
    categorical_summary: Dict[str, CategoricalSummary]
    charts: List[ChartData]

class KeywordItem(BaseModel):
    word: str
    score: float

class TextResult(BaseModel):
    summary: str
    keywords: List[KeywordItem]
    word_count: int
    page_count: Optional[int] = None
    paragraph_count: Optional[int] = None
    ai_model: str

class UploadResponse(BaseModel):
    file_name: str
    file_type: str
    data_category: str
    tabular: Optional[TabularResult] = None
    text: Optional[TextResult] = None
