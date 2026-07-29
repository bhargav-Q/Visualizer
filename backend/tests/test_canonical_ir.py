"""
Unit and Contract Verification Tests for Phase 1: Canonical Document IR
"""
import pytest
from uuid import UUID
from ir.confidence import ConfidenceObject, ConfidenceFactors, ElementConfidenceMap
from ir.provenance import ProvenanceRecord, ProvenanceStep
from ir.relationships import NodeRelationship, RelationshipType
from ir.nodes import HeaderNode, ParagraphNode, TableNode, CellNode, ImageNode, ListNode
from ir.document import CanonicalDocumentIR

def test_confidence_object_model():
    conf = ConfidenceObject(
        score=0.95,
        level="HIGH",
        extraction_method="pymupdf_digital",
        factors=ConfidenceFactors(ocr_confidence=0.98, alignment_score=1.0)
    )
    assert conf.score == 0.95
    assert conf.level == "HIGH"
    assert conf.factors.ocr_confidence == 0.98

def test_provenance_record():
    step = ProvenanceStep(stage_name="parse", processor_name="PyMuPDFAdapter", execution_time_ms=12.5)
    prov = ProvenanceRecord(created_by="PDFParser", source_filename="sample.pdf", steps=[step])
    assert prov.created_by == "PDFParser"
    assert len(prov.steps) == 1
    assert prov.steps[0].stage_name == "parse"

def test_canonical_document_ir_ast():
    h1 = HeaderNode(level=1, text="Executive Summary", page_number=1, bbox=[72.0, 72.0, 540.0, 90.0])
    p1 = ParagraphNode(text="Revenue grew by 15% in Q1 2026.", page_number=1, bbox=[72.0, 100.0, 540.0, 140.0])
    
    cell1 = CellNode(row_index=0, col_index=0, raw_text="Q1 2026", value="Q1 2026")
    cell2 = CellNode(row_index=0, col_index=1, raw_text="4200000", value=4200000, data_type="number")
    tbl = TableNode(
        table_title="Financial Summary",
        headers=["Quarter", "Revenue"],
        rows=[["Q1 2026", 4200000]],
        cell_matrix=[[cell1, cell2]],
        row_count=1,
        col_count=2,
        page_number=1
    )

    rel = NodeRelationship(
        source_node_id=h1.node_id,
        target_node_id=p1.node_id,
        relationship_type=RelationshipType.CONTAINS
    )

    doc_ir = CanonicalDocumentIR(
        filename="financial_report.pdf",
        file_type="pdf",
        raw_text="Executive Summary\nRevenue grew by 15% in Q1 2026.",
        nodes=[h1, p1, tbl],
        relationships=[rel]
    )

    assert isinstance(doc_ir.document_id, UUID)
    assert len(doc_ir.nodes) == 3
    assert len(doc_ir.get_headers()) == 1
    assert len(doc_ir.get_paragraphs()) == 1
    assert len(doc_ir.get_tables()) == 1
    assert doc_ir.get_headers()[0].text == "Executive Summary"
    assert doc_ir.get_tables()[0].rows[0][1] == 4200000
