from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from models.schemas import NumericSummary, CategoricalSummary, KeywordItem

class ColumnProfile(BaseModel):
    """Profile metadata describing a single dataset column."""
    name: str
    dtype: str  # "numeric", "datetime", "string"
    missing_count: int = 0
    unique_count: int = 0
    is_discrete: bool = False

class DocumentProfile(BaseModel):
    """Complete structural and statistical profiling contract for a document dataset."""
    filename: str
    file_type: str
    data_category: str
    row_count: int = 0
    col_count: int = 0
    columns: List[ColumnProfile] = Field(default_factory=list)
    numeric_summaries: Dict[str, NumericSummary] = Field(default_factory=dict)
    categorical_summaries: Dict[str, CategoricalSummary] = Field(default_factory=dict)
    word_count: int = 0
    summary: str = ""
    keywords: List[KeywordItem] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
