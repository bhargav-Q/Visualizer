from pydantic import BaseModel, Field
from uuid import UUID, uuid4
from typing import List, Dict, Any, Optional
from ir.nodes import IRNode, TableNode, HeaderNode, ParagraphNode
from ir.relationships import NodeRelationship
from ir.confidence import ElementConfidenceMap
from ir.provenance import ProvenanceRecord

class CanonicalDocumentIR(BaseModel):
    """
    Canonical Document Intermediate Representation (IR).
    Single Source of Truth AST representing structured document content,
    spatial bounding boxes, provenance, confidence, and relationships.
    """
    document_id: UUID = Field(default_factory=uuid4)
    filename: str
    file_type: str
    raw_text: str = ""
    nodes: List[IRNode] = Field(default_factory=list)
    relationships: List[NodeRelationship] = Field(default_factory=list)
    confidence_map: ElementConfidenceMap = Field(default_factory=ElementConfidenceMap)
    provenance: Optional[ProvenanceRecord] = None
    warnings: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @property
    def data_category(self) -> str:
        """Determines if the document is primarily tabular or qualitative text."""
        return "tabular" if len(self.get_tables()) > 0 else "text"

    @property
    def tables(self) -> List[TableNode]:
        """Property accessor returning all TableNode instances in document AST."""
        return self.get_tables()

    def get_tables(self) -> List[TableNode]:
        """Convenience accessor returning all TableNode instances in document AST."""
        return [node for node in self.nodes if isinstance(node, TableNode) or getattr(node, "node_type", None) == "table"]

    def get_headers(self) -> List[HeaderNode]:
        """Convenience accessor returning all HeaderNode instances in document AST."""
        return [node for node in self.nodes if isinstance(node, HeaderNode) or getattr(node, "node_type", None) == "header"]

    def get_paragraphs(self) -> List[ParagraphNode]:
        """Convenience accessor returning all ParagraphNode instances in document AST."""
        return [node for node in self.nodes if isinstance(node, ParagraphNode) or getattr(node, "node_type", None) == "paragraph"]
