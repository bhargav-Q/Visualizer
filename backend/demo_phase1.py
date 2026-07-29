"""
Interactive Manual Demo for Phase 1: Canonical Document IR
Run this script via terminal:
    cd backend
    ..\.venv\Scripts\python.exe demo_phase1.py
"""

from uuid import uuid4
from ir.confidence import ConfidenceObject, ConfidenceFactors
from ir.provenance import ProvenanceRecord, ProvenanceStep
from ir.relationships import NodeRelationship, RelationshipType
from ir.nodes import HeaderNode, ParagraphNode, TableNode, CellNode
from ir.document import CanonicalDocumentIR

def run_manual_demo():
    print("=" * 70)
    print(" VISUALIZER: CANONICAL DOCUMENT IR (PHASE 1 MANUAL DEMO)")
    print("=" * 70)

    # 1. Create Provenance Record
    step = ProvenanceStep(
        stage_name="parse",
        processor_name="PyMuPDFAdapter",
        version="1.0.0",
        execution_time_ms=14.2
    )
    provenance = ProvenanceRecord(
        created_by="PDFParserAdapter",
        source_filename="Annual_Report_2026.pdf",
        source_hash_sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        steps=[step]
    )

    # 2. Build Document Nodes with Spatial Bounding Boxes & Multi-Factored Confidence
    header = HeaderNode(
        level=1,
        text="Q1 Executive Summary",
        page_number=1,
        bbox=[72.0, 72.0, 540.0, 95.0],
        confidence=ConfidenceObject(
            score=0.98,
            level="HIGH",
            extraction_method="pymupdf_digital",
            factors=ConfidenceFactors(ocr_confidence=1.0, alignment_score=1.0)
        )
    )

    paragraph = ParagraphNode(
        text="Total Q1 revenue reached $4.2M, representing 15% growth year-over-year.",
        page_number=1,
        bbox=[72.0, 105.0, 540.0, 140.0],
        confidence=ConfidenceObject(
            score=0.95,
            level="HIGH",
            extraction_method="pymupdf_digital"
        )
    )

    cell1 = CellNode(row_index=0, col_index=0, raw_text="Quarter", value="Quarter", data_type="string")
    cell2 = CellNode(row_index=0, col_index=1, raw_text="Revenue", value="Revenue", data_type="string")
    cell3 = CellNode(row_index=1, col_index=0, raw_text="Q1 2026", value="Q1 2026", data_type="string")
    cell4 = CellNode(row_index=1, col_index=1, raw_text="$4,200,000", value=4200000, data_type="number")

    table = TableNode(
        table_title="Quarterly Performance Summary",
        headers=["Quarter", "Revenue"],
        rows=[["Quarter", "Revenue"], ["Q1 2026", 4200000]],
        cell_matrix=[[cell1, cell2], [cell3, cell4]],
        row_count=2,
        col_count=2,
        page_number=1,
        bbox=[72.0, 150.0, 540.0, 280.0],
        confidence=ConfidenceObject(
            score=0.92,
            level="HIGH",
            extraction_method="rapidocr_spatial_grid"
        )
    )

    # 3. Create Directed Relationship Graph Edges
    rel = NodeRelationship(
        source_node_id=header.node_id,
        target_node_id=paragraph.node_id,
        relationship_type=RelationshipType.CONTAINS
    )

    # 4. Construct Root Canonical Document IR
    doc_ir = CanonicalDocumentIR(
        filename="Annual_Report_2026.pdf",
        file_type="pdf",
        raw_text=f"{header.text}\n{paragraph.text}",
        nodes=[header, paragraph, table],
        relationships=[rel],
        provenance=provenance
    )

    # 5. Output Inspection
    print(f"\n- Document ID:       {doc_ir.document_id}")
    print(f"- Filename:          {doc_ir.filename} ({doc_ir.file_type.upper()})")
    print(f"- Created By:        {doc_ir.provenance.created_by}")
    print(f"- Parse Execution:   {doc_ir.provenance.steps[0].execution_time_ms} ms")
    print(f"\n- AST Node Tree Breakdown:")
    print(f"  * Total AST Nodes:   {len(doc_ir.nodes)}")
    print(f"  * Headings Count:    {len(doc_ir.get_headers())} -> '{doc_ir.get_headers()[0].text}' (H{doc_ir.get_headers()[0].level})")
    print(f"  * Paragraphs Count:  {len(doc_ir.get_paragraphs())}")
    print(f"  * Tables Count:      {len(doc_ir.get_tables())} -> Title: '{doc_ir.get_tables()[0].table_title}'")
    print(f"    - Grid Matrix:     {doc_ir.get_tables()[0].row_count} rows x {doc_ir.get_tables()[0].col_count} columns")
    print(f"    - Parsed Cell Num: {doc_ir.get_tables()[0].cell_matrix[1][1].value} ({type(doc_ir.get_tables()[0].cell_matrix[1][1].value).__name__})")
    print(f"\n- Directed Relationship Edge:")
    print(f"  * {rel.relationship_type.value}: Header[{header.node_id}] ---> Paragraph[{paragraph.node_id}]")
    print(f"\n- Multi-Factored Confidence Object:")
    print(f"  * Table Confidence Score: {table.confidence.score} ({table.confidence.level})")
    print(f"  * Extraction Method:      {table.confidence.extraction_method}")
    print("=" * 70)
    print(" SUCCESS: Phase 1 Manual Verification Completed!")
    print("=" * 70)

if __name__ == "__main__":
    run_manual_demo()
