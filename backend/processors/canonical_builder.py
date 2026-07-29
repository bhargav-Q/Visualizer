import re
from typing import Optional, List, Dict, Any
from ir.document import CanonicalDocumentIR
from ir.nodes import HeaderNode, ParagraphNode, TableNode, CellNode, ListNode
from ir.confidence import ConfidenceObject, ConfidenceFactors, ElementConfidenceMap
from ir.provenance import ProvenanceRecord, ProvenanceStep
from ir.relationships import NodeRelationship, RelationshipType
from contracts.document import UnifiedDocumentModel, DocumentContent, TableData

class CanonicalIRBuilder:
    """
    Builder service converting UnifiedDocumentModel and raw DocumentContent 
    into a strongly-typed CanonicalDocumentIR AST graph with provenance and confidence.
    """

    @staticmethod
    def build_ir(
        model: UnifiedDocumentModel,
        content: Optional[DocumentContent] = None,
        parser_name: str = "BaseParserAdapter",
        execution_time_ms: float = 0.0
    ) -> CanonicalDocumentIR:
        
        filename = model.filename or "document"
        file_type = model.file_type or "unknown"

        # 1. Build Provenance Record
        provenance = ProvenanceRecord(
            created_by=parser_name,
            source_filename=filename,
            steps=[
                ProvenanceStep(
                    stage_name="parse",
                    processor_name=parser_name,
                    version="1.0.0",
                    execution_time_ms=execution_time_ms
                )
            ]
        )

        nodes = []
        relationships = []
        element_confidence = {}

        # 2. Extract Headings & Paragraph Nodes from Raw Text
        lines = [l.strip() for l in (model.raw_text or "").split("\n") if l.strip()]
        current_header: Optional[HeaderNode] = None
        current_page = 1

        for line in lines:
            if line.startswith("--- Page "):
                try:
                    current_page = int(re.sub(r"\D", "", line) or 1)
                except Exception:
                    pass
                continue

            # Identify Headings vs Paragraphs
            if line.startswith("# ") or (len(line) < 60 and line.isupper() and not line.isdigit()):
                clean_title = line.lstrip("# ").strip()
                h_level = 1 if not line.startswith("##") else 2
                h_node = HeaderNode(
                    level=h_level,
                    text=clean_title,
                    page_number=current_page,
                    confidence=ConfidenceObject(score=0.98, level="HIGH", extraction_method="text_heading_heuristic")
                )
                nodes.append(h_node)
                current_header = h_node
                element_confidence[str(h_node.node_id)] = h_node.confidence
            else:
                p_node = ParagraphNode(
                    text=line,
                    page_number=current_page,
                    confidence=ConfidenceObject(score=0.95, level="HIGH", extraction_method="text_paragraph_parser")
                )
                nodes.append(p_node)
                element_confidence[str(p_node.node_id)] = p_node.confidence

                # Connect relationship edge if under a section header
                if current_header:
                    rel = NodeRelationship(
                        source_node_id=current_header.node_id,
                        target_node_id=p_node.node_id,
                        relationship_type=RelationshipType.CONTAINS
                    )
                    relationships.append(rel)

        # 3. Convert Tables into TableNode and CellNode AST Matrices
        for tbl in (model.tables or []):
            headers = tbl.headers or []
            rows = tbl.rows or []
            title = tbl.table_title or "Extracted Table"

            cell_matrix: List[List[CellNode]] = []
            for r_idx, row in enumerate(rows):
                cell_row: List[CellNode] = []
                for c_idx, cell_val in enumerate(row):
                    cell_str = str(cell_val) if cell_val is not None else ""
                    val_typed = cell_val
                    data_type = "string"

                    if isinstance(cell_val, (int, float)):
                        data_type = "number"
                    elif cell_val is not None and cell_str.replace(".", "", 1).isdigit():
                        try:
                            val_typed = float(cell_str) if "." in cell_str else int(cell_str)
                            data_type = "number"
                        except ValueError:
                            pass

                    c_node = CellNode(
                        row_index=r_idx,
                        col_index=c_idx,
                        raw_text=cell_str,
                        value=val_typed,
                        data_type=data_type,
                        confidence=ConfidenceObject(score=0.92, level="HIGH", extraction_method="table_grid_cell")
                    )
                    cell_row.append(c_node)
                cell_matrix.append(cell_row)

            tbl_node = TableNode(
                table_title=title,
                headers=headers,
                rows=rows,
                cell_matrix=cell_matrix,
                row_count=len(rows),
                col_count=len(headers) if headers else (len(rows[0]) if rows else 0),
                page_number=1,
                confidence=ConfidenceObject(score=0.92, level="HIGH", extraction_method="tabular_matrix_converter")
            )
            nodes.append(tbl_node)
            element_confidence[str(tbl_node.node_id)] = tbl_node.confidence

        # Build Confidence Map
        confidence_map = ElementConfidenceMap(
            document_confidence=ConfidenceObject(score=0.96, level="HIGH", extraction_method="canonical_ir_builder"),
            element_confidence=element_confidence
        )

        return CanonicalDocumentIR(
            filename=filename,
            file_type=file_type,
            raw_text=model.raw_text or "",
            nodes=nodes,
            relationships=relationships,
            confidence_map=confidence_map,
            provenance=provenance
        )
