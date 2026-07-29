"""
Unit and Integration Verification Tests for Phase 2: Stateless Exporters
"""
import pytest
from ir.nodes import HeaderNode, ParagraphNode, TableNode, CellNode
from ir.document import CanonicalDocumentIR
from exporters.markdown_exporter import MarkdownExporter
from exporters.html_exporter import HTMLExporter
from exporters.rag_exporter import RAGChunkExporter
from exporters.dashboard_exporter import DashboardExporter
from models.schemas import UploadResponse

@pytest.fixture
def sample_doc_ir():
    h1 = HeaderNode(level=1, text="Executive Summary", page_number=1)
    p1 = ParagraphNode(text="Q1 Revenue reached $4.2M, representing 15% growth.", page_number=1)
    cell1 = CellNode(row_index=0, col_index=0, raw_text="Q1 2026", value="Q1 2026")
    cell2 = CellNode(row_index=0, col_index=1, raw_text="4200000", value=4200000)
    tbl = TableNode(
        table_title="Financial Performance",
        headers=["Quarter", "Revenue"],
        rows=[["Q1 2026", 4200000]],
        cell_matrix=[[cell1, cell2]],
        row_count=1,
        col_count=2,
        page_number=1
    )
    return CanonicalDocumentIR(
        filename="annual_report.pdf",
        file_type="pdf",
        raw_text="Executive Summary\nQ1 Revenue reached $4.2M.",
        nodes=[h1, p1, tbl]
    )

def test_markdown_exporter(sample_doc_ir):
    exporter = MarkdownExporter()
    md_output = exporter.export(sample_doc_ir)
    assert "# Executive Summary" in md_output
    assert "Q1 Revenue reached $4.2M" in md_output
    assert "| Quarter | Revenue |" in md_output
    assert "| Q1 2026 | 4200000 |" in md_output

def test_html_exporter(sample_doc_ir):
    exporter = HTMLExporter()
    html_output = exporter.export(sample_doc_ir)
    assert "<h1>Executive Summary</h1>" in html_output
    assert "<p>Q1 Revenue reached $4.2M, representing 15% growth.</p>" in html_output
    assert "<table class=\"data-table\">" in html_output
    assert "<th>Quarter</th>" in html_output

def test_rag_exporter(sample_doc_ir):
    exporter = RAGChunkExporter()
    chunks = exporter.export(sample_doc_ir)
    assert len(chunks) == 1
    assert chunks[0].section_title == "Executive Summary"
    assert "Q1 Revenue reached $4.2M" in chunks[0].content
    assert chunks[0].page_number == 1

def test_dashboard_exporter(sample_doc_ir):
    exporter = DashboardExporter()
    res = exporter.export(sample_doc_ir, processing_time=0.15)
    assert isinstance(res, UploadResponse)
    assert res.file_name == "annual_report.pdf"
    assert res.file_type == "pdf"
    assert res.processing_time == 0.15
