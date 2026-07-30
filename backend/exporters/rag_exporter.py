# ==============================================================================
# RAG EXPORTER (DEPRECATED & COMMENTED OUT FOR MISTRAL OCR)
# All original lines preserved below as comments.
# ==============================================================================
# from pydantic import BaseModel, Field
# from typing import List, Dict, Any, Optional
# from exporters.base import BaseExporter
# from ir.document import CanonicalDocumentIR
# from ir.nodes import HeaderNode, ParagraphNode, TableNode
# 
# class RAGChunk(BaseModel):
#     """Semantic vector chunk representation for RAG and search indexers."""
#     chunk_id: str
#     section_title: str
#     content: str
#     page_number: int
#     bbox: Optional[List[float]] = None
#     metadata: Dict[str, Any] = Field(default_factory=dict)
# 
# class RAGChunkExporter(BaseExporter):
#     """
#     Stateless read-only exporter splitting CanonicalDocumentIR AST
#     into semantic section chunks carrying spatial bounding boxes for Vector Databases.
#     """
# 
#     def export(self, doc_ir: CanonicalDocumentIR, max_chunk_words: int = 250, **kwargs) -> List[RAGChunk]:
#         if not doc_ir or not doc_ir.nodes:
#             return []
# 
#         chunks: List[RAGChunk] = []
#         current_section = "Overview"
#         current_content = []
#         current_page = 1
#         current_bbox = None
# 
#         for idx, node in enumerate(doc_ir.nodes):
#             if isinstance(node, HeaderNode) or getattr(node, "node_type", None) == "header":
#                 # Flush previous section chunk if non-empty
#                 if current_content:
#                     chunk_text = "\n".join(current_content).strip()
#                     if chunk_text:
#                         chunks.append(RAGChunk(
#                             chunk_id=f"{doc_ir.filename}_chunk_{len(chunks)+1}",
#                             section_title=current_section,
#                             content=chunk_text,
#                             page_number=current_page,
#                             bbox=current_bbox,
#                             metadata={"file_name": doc_ir.filename, "file_type": doc_ir.file_type}
#                         ))
#                     current_content = []
# 
#                 current_section = getattr(node, "text", "Section")
#                 current_page = getattr(node, "page_number", 1) or 1
#                 current_bbox = getattr(node, "bbox", None)
# 
#             elif isinstance(node, ParagraphNode) or getattr(node, "node_type", None) == "paragraph":
#                 p_text = getattr(node, "text", "")
#                 if p_text:
#                     current_content.append(p_text)
#                     if not current_bbox:
#                         current_bbox = getattr(node, "bbox", None)
# 
#             elif isinstance(node, TableNode) or getattr(node, "node_type", None) == "table":
#                 headers = getattr(node, "headers", [])
#                 rows = getattr(node, "rows", [])
#                 table_lines = []
#                 if headers:
#                     table_lines.append("| " + " | ".join(str(h) for h in headers) + " |")
#                 for r in rows:
#                     table_lines.append("| " + " | ".join(str(c) if c is not None else "" for c in r) + " |")
#                 
#                 if table_lines:
#                     current_content.append("\n".join(table_lines))
# 
#         # Flush final remaining section
#         if current_content:
#             chunk_text = "\n".join(current_content).strip()
#             if chunk_text:
#                 chunks.append(RAGChunk(
#                     chunk_id=f"{doc_ir.filename}_chunk_{len(chunks)+1}",
#                     section_title=current_section,
#                     content=chunk_text,
#                     page_number=current_page,
#                     bbox=current_bbox,
#                     metadata={"file_name": doc_ir.filename, "file_type": doc_ir.file_type}
#                 ))
# 
#         return chunks

class RAGChunkExporter:
    """Stub class preserving import safety."""
    def export(self, *args, **kwargs):
        return []
