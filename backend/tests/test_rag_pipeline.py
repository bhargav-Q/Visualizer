"""
End-to-End RAG Vector Chunking and Provenance Integration Tests — Phase 4 Verification
"""
import pytest
from parsers.factory import get_parser_factory
from processors.normalizer import DocumentNormalizer
from processors.canonical_builder import CanonicalIRBuilder
from exporters.rag_exporter import RAGChunkExporter, RAGChunk
from exporters.markdown_exporter import MarkdownExporter
from exporters.html_exporter import HTMLExporter

def test_pdf_rag_vector_chunking():
    pdf_text = """# Executive Financial Summary
Q1 Revenue reached $4.2M representing a 15% increase year-over-year.

# Regional Division Breakdown
North America generated $2.8M while APAC contributed $1.4M in total gross sales."""

    parser_factory = get_parser_factory()
    content = parser_factory.get_parser(pdf_text.encode("utf-8"), "report.txt").parse(pdf_text.encode("utf-8"), "report.txt")
    model = DocumentNormalizer.normalize(content, "report.txt", "txt")
    doc_ir = CanonicalIRBuilder.build_ir(model, content=content, parser_name="TXTParserAdapter")

    rag_exporter = RAGChunkExporter()
    chunks = rag_exporter.export(doc_ir)

    assert len(chunks) >= 2
    assert chunks[0].section_title in ("Overview", "Executive Financial Summary")
    assert "Q1 Revenue reached $4.2M" in chunks[0].content or "Q1 Revenue reached $4.2M" in chunks[1].content
    assert chunks[0].metadata["file_name"] == "report.txt"

def test_exporters_immutability():
    """Verifies that running multiple exporters on the same AST does not mutate node graph state."""
    text_content = "# Section 1\nParagraph text line 1.\n\n# Section 2\nParagraph text line 2."
    parser_factory = get_parser_factory()
    content = parser_factory.get_parser(text_content.encode("utf-8"), "doc.txt").parse(text_content.encode("utf-8"), "doc.txt")
    model = DocumentNormalizer.normalize(content, "doc.txt", "txt")
    doc_ir = CanonicalIRBuilder.build_ir(model, content=content)

    initial_node_count = len(doc_ir.nodes)

    md_out = MarkdownExporter().export(doc_ir)
    html_out = HTMLExporter().export(doc_ir)
    rag_out = RAGChunkExporter().export(doc_ir)

    assert len(doc_ir.nodes) == initial_node_count
    assert "# Section 1" in md_out
    assert "<h1>Section 1</h1>" in html_out
    assert len(rag_out) >= 1
