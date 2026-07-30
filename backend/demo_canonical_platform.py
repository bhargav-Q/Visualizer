# ==============================================================================
# CANONICAL IR PLATFORM DEMO (DEPRECATED & COMMENTED OUT FOR MISTRAL OCR)
# All original lines preserved below as comments.
# ==============================================================================
# """
# Complete End-to-End Canonical Document IR Platform Verification Script
# Run via terminal:
#     cd backend
#     ..\.venv\Scripts\python.exe demo_canonical_platform.py
# """
# 
# from parsers.factory import get_parser_factory
# from processors.normalizer import DocumentNormalizer
# from processors.canonical_builder.py import CanonicalIRBuilder
# from exporters.markdown_exporter import MarkdownExporter
# from exporters.html_exporter import HTMLExporter
# from exporters.rag_exporter import RAGChunkExporter
# from exporters.dashboard_exporter import DashboardExporter
# from services.pipeline_service import get_pipeline_service
# 
# def run_platform_demo():
#     print("=" * 75)
#     print(" VISUALIZER: CANONICAL DOCUMENT IR PLATFORM DEMO (PHASE 4)")
#     print("=" * 75)
# 
#     sample_doc_text = """# Visualizer Document Intelligence Platform
# The Canonical Document IR acts as the single source of truth AST.
# 
# # Performance & Benchmarks
# Tabular data matrices are stored with zero-copy memory buffers.
# 
# | Quarter | Sales | Growth |
# | Q1 2026 | 4200000 | 15% |
# | Q2 2026 | 4800000 | 14% |
# """
# 
#     filename = "platform_overview.txt"
#     file_bytes = sample_doc_text.encode("utf-8")
# 
#     # 1. Pipeline Execution
#     service = get_pipeline_service()
#     response = service.process_document(file_bytes, filename)
# 
#     print(f"\n- 1. LIVE PIPELINE RESPONSE:")
#     print(f"  * Status:           200 OK")
#     print(f"  * Filename:         {response.file_name} ({response.file_type.upper()})")
#     print(f"  * Data Category:    {response.data_category}")
#     print(f"  * Processing Time:  {response.processing_time}s")
# 
#     # 2. Re-construct Canonical AST to demonstrate multi-exporter outputs
#     parser_factory = get_parser_factory()
#     content = parser_factory.get_parser(file_bytes, filename).parse(file_bytes, filename)
#     model = DocumentNormalizer.normalize(content, filename, "txt")
#     doc_ir = CanonicalIRBuilder.build_ir(model, content=content, parser_name="TXTParserAdapter")
# 
#     print(f"\n- 2. CANONICAL DOCUMENT IR AST:")
#     print(f"  * Document ID:      {doc_ir.document_id}")
#     print(f"  * Total AST Nodes:  {len(doc_ir.nodes)}")
#     print(f"  * Headings:         {len(doc_ir.get_headers())}")
#     print(f"  * Paragraphs:       {len(doc_ir.get_paragraphs())}")
#     print(f"  * Tables:           {len(doc_ir.get_tables())}")
# 
#     # 3. Read-Only Exporters Demonstration
#     md_exporter = MarkdownExporter()
#     html_exporter = HTMLExporter()
#     rag_exporter = RAGChunkExporter()
# 
#     md_output = md_exporter.export(doc_ir)
#     html_output = html_exporter.export(doc_ir)
#     rag_chunks = rag_exporter.export(doc_ir)
# 
#     print(f"\n- 3. MARKDOWN EXPORTER OUTPUT:")
#     print("-" * 50)
#     print(md_output[:300] + "...")
# 
#     print(f"\n- 4. HTML EXPORTER OUTPUT:")
#     print("-" * 50)
#     print(html_output[:250] + "...")
# 
#     print(f"\n- 5. RAG VECTOR CHUNKS EXPORTER OUTPUT:")
#     print("-" * 50)
#     for i, chunk in enumerate(rag_chunks):
#         print(f"  * Chunk {i+1} [{chunk.chunk_id}]: Section='{chunk.section_title}' ({len(chunk.content.split())} words)")
# 
#     print("=" * 75)
#     print(" SUCCESS: Canonical Document IR Platform Verification Completed!")
#     print("=" * 75)

if __name__ == "__main__":
    print("Canonical IR Platform Demo disabled.")
