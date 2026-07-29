from exporters.base import BaseExporter
from ir.document import CanonicalDocumentIR
from ir.nodes import HeaderNode, ParagraphNode, TableNode, ImageNode, ListNode

class MarkdownExporter(BaseExporter):
    """
    Stateless read-only exporter converting CanonicalDocumentIR AST
    into clean, human-readable Markdown text without inline comment bloat.
    """

    def export(self, doc_ir: CanonicalDocumentIR, **kwargs) -> str:
        if not doc_ir or not doc_ir.nodes:
            return doc_ir.raw_text if doc_ir else ""

        markdown_lines = []
        current_page = None

        for node in doc_ir.nodes:
            # Emit page boundary marker if page changes
            if node.page_number and node.page_number != current_page:
                current_page = node.page_number
                if current_page > 1:
                    markdown_lines.append(f"\n--- Page {current_page} ---\n")

            if isinstance(node, HeaderNode) or getattr(node, "node_type", None) == "header":
                level = getattr(node, "level", 1)
                text = getattr(node, "text", "")
                markdown_lines.append(f"{'#' * level} {text}\n")

            elif isinstance(node, ParagraphNode) or getattr(node, "node_type", None) == "paragraph":
                text = getattr(node, "text", "")
                markdown_lines.append(f"{text}\n")

            elif isinstance(node, TableNode) or getattr(node, "node_type", None) == "table":
                headers = getattr(node, "headers", [])
                rows = getattr(node, "rows", [])
                table_title = getattr(node, "table_title", None)

                if table_title:
                    markdown_lines.append(f"**Table: {table_title}**\n")

                if headers:
                    markdown_lines.append("| " + " | ".join(str(h) for h in headers) + " |")
                    markdown_lines.append("| " + " | ".join("---" for _ in headers) + " |")

                for row in rows:
                    markdown_lines.append("| " + " | ".join(str(c) if c is not None else "" for c in row) + " |")
                markdown_lines.append("")

            elif isinstance(node, ListNode) or getattr(node, "node_type", None) == "list":
                is_ordered = getattr(node, "is_ordered", False)
                items = getattr(node, "items", [])
                for idx, item in enumerate(items):
                    prefix = f"{idx + 1}." if is_ordered else "-"
                    markdown_lines.append(f"{prefix} {item}")
                markdown_lines.append("")

            elif isinstance(node, ImageNode) or getattr(node, "node_type", None) == "image":
                caption = getattr(node, "caption", "Figure")
                img_id = getattr(node, "image_id", "img")
                markdown_lines.append(f"![{caption}]({img_id})\n")

        return "\n".join(markdown_lines).strip()
