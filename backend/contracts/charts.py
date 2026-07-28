from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from models.schemas import ChartData

class ChartSpec(BaseModel):
    """Specification contract for front-end visual chart rendering."""
    type: str  # "line", "bar"
    title: str
    x_key: str
    y_key: str
    data: List[Dict[str, Any]] = Field(default_factory=list)

class ChartRecommendation(BaseModel):
    """Recommendation contract produced by VisualizationRecommender."""
    chart_type: str
    title: str
    x_key: str
    y_key: str
    score: float = 1.0
    reasoning: str = ""
    chart_spec: ChartSpec
