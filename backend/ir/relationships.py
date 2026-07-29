from pydantic import BaseModel, Field
from uuid import UUID, uuid4
from enum import Enum
from typing import Dict, Any

class RelationshipType(str, Enum):
    CONTAINS = "CONTAINS"              # Section -> Paragraph
    CAPTIONS = "CAPTIONS"              # Caption -> Image/Table
    REFERENCES = "REFERENCES"          # Summary -> Paragraph / Chart -> Table
    EXTRACTED_FROM = "EXTRACTED_FROM"  # Metric -> Cell
    CORRESPONDS_TO = "CORRESPONDS_TO"  # Traceability match

class NodeRelationship(BaseModel):
    """Explicit directed relationship edge between two IR nodes."""
    relationship_id: UUID = Field(default_factory=uuid4)
    source_node_id: UUID
    target_node_id: UUID
    relationship_type: RelationshipType
    confidence_score: float = 1.0
    metadata: Dict[str, Any] = Field(default_factory=dict)
