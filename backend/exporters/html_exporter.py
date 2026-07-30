# ==============================================================================
# HTML EXPORTER (DEPRECATED & COMMENTED OUT FOR MISTRAL OCR)
# All original lines preserved below as comments.
# ==============================================================================
# import html
# from exporters.base import BaseExporter
# from ir.document import CanonicalDocumentIR
# from ir.nodes import HeaderNode, ParagraphNode, TableNode, ImageNode, ListNode
# 
# class HTMLExporter(BaseExporter):
#     """
#     Stateless read-only exporter converting CanonicalDocumentIR AST
#     into clean, semantic HTML5 markup for browser and dashboard rendering.
#     """
# 
#     def export(self, doc_ir: CanonicalDocumentIR, **kwargs) -> str:
#         if not doc_ir or not doc_ir.nodes:
#             return f"<div>{html.escape(doc_ir.raw_text)}</div>" if doc_ir else ""
# 
#         html_snippets = ["<div class=\"canonical-document-body\">"]
# 
#         for node in doc_ir.nodes:
#             if isinstance(node, HeaderNode) or getattr(node, "node_type", None) == "header":
#                 level = getattr(node, "level", 1)
#                 text = html.escape(getattr(node, "text", ""))
#                 html_snippets.append(f"<h{level}>{text}</h{level}>")
# 
#             elif isinstance(node, ParagraphNode) or getattr(node, "node_type", None) == "paragraph":
#                 text = html.escape(getattr(node, "text", ""))
#                 html_snippets.append(f"<p>{text}</p>")
# 
#             elif isinstance(node, TableNode) or getattr(node, "node_type", None) == "table":
#                 headers = getattr(node, "headers", [])
#                 rows = getattr(node, "rows", [])
#                 table_title = getattr(node, "table_title", None)
# 
#                 html_snippets.append("<table class=\"data-table\">")
#                 if table_title:
#                     html_snippets.append(f"<caption>{html.escape(table_title)}</caption>")
# 
#                 if headers:
#                     html_snippets.append("<thead><tr>")
#                     for h in headers:
#                         html_snippets.append(f"<th>{html.escape(str(h))}</th>")
#                     html_snippets.append("</tr></thead>")
# 
#                 if rows:
#                     html_snippets.append("tbody>")
#                     for row in rows:
#                         html_snippets.append("<tr>")
#                         for cell in row:
#                             cell_str = str(cell) if cell is not None else ""
#                             html_snippets.append(f"<td>{html.escape(cell_str)}</td>")
#                         html_snippets.append("</tr>")
#                     html_snippets.append("</tbody>")
# 
#                 html_snippets.append("</table>")
# 
#             elif isinstance(node, ListNode) or getattr(node, "node_type", None) == "list":
#                 is_ordered = getattr(node, "is_ordered", False)
#                 items = getattr(node, "items", [])
#                 tag = "ol" if is_ordered else "ul"
#                 html_snippets.append(f"<{tag}>")
#                 for item in items:
#                     html_snippets.append(f"<li>{html.escape(str(item))}</li>")
#                 html_snippets.append(f"</{tag}>")
# 
#         html_snippets.append("</div>")
#         return "\n".join(html_snippets)

class HTMLExporter:
    """Stub class preserving import safety."""
    def export(self, *args, **kwargs) -> str:
        return ""
