import os
import logging
from services.mistral_ocr_service import process_document_with_mistral_ocr
from services.tabular_service import process_tabular_file
from services.dashboard_agent import generate_dashboard_spec_from_markdown

logger = logging.getLogger(__name__)

def run_file_to_dashboard_pipeline(
    file_path: str = None,
    file_bytes: bytes = None,
    filename: str = None,
    output_dir: str = "./outputs"
) -> dict:
    """
    Master pipeline orchestrator connecting Mistral OCR, Tabular engine, 
    and NVIDIA NIM DeepSeek-V4-Flash to produce unified dashboard JSON specifications.
    Supports disk file paths and byte buffer inputs.
    """
    os.makedirs(output_dir, exist_ok=True)
    
    if file_path:
        filename = filename or os.path.basename(file_path)
    elif not filename:
        raise ValueError("Either file_path or filename must be provided.")

    base_name = os.path.splitext(filename)[0]
    file_ext = filename.split(".")[-1].lower() if "." in filename else "pdf"

    # BRANCH 1: Tabular Files (CSV / XLSX / XLS) -> Native Engine
    if file_ext in ["csv", "xlsx", "xls"]:
        logger.info(f"[PIPELINE] Processing tabular file '{filename}' via native pandas engine.")
        return process_tabular_file(
            file_path=file_path,
            file_bytes=file_bytes,
            filename=filename
        )

    # BRANCH 2: Unstructured Files (PDF / Images / Docs) -> Mistral OCR + DeepSeek-V4-Flash Agent
    elif file_ext in ["pdf", "png", "jpg", "jpeg", "webp", "docx", "txt"]:
        logger.info(f"[PIPELINE] Processing document '{filename}' via Mistral OCR + DeepSeek-V4-Flash Agent.")
        output_md_path = os.path.join(output_dir, f"{base_name}.md")
        
        ocr_result = process_document_with_mistral_ocr(
            file_path=file_path,
            file_bytes=file_bytes,
            filename=filename,
            output_md_path=output_md_path
        )

        resolved_markdown = ocr_result.get("markdown_text", "")

        # Synthesize Dashboard Spec via DeepSeek-V4-Flash Model
        dashboard_spec = generate_dashboard_spec_from_markdown(resolved_markdown)

        keywords_list = dashboard_spec.get("keywords", [])
        return {
            "status": "success",
            "source_type": "unstructured",
            "file_name": filename,
            "file_type": file_ext,
            "data_category": "text",
            "dashboard_title": dashboard_spec.get("dashboard_title", filename),
            "executive_summary": dashboard_spec.get("executive_summary", ""),
            "kpis": dashboard_spec.get("kpis", []),
            "keywords": keywords_list,
            "charts": dashboard_spec.get("charts", []),
            "raw_markdown": resolved_markdown,
            "page_count": ocr_result.get("page_count", 1),
            "text": {
                "summary": dashboard_spec.get("executive_summary", ""),
                "keywords": keywords_list,
                "word_count": len(resolved_markdown.split()),
                "page_count": ocr_result.get("page_count", 1),
                "paragraph_count": len([p for p in resolved_markdown.split("\n\n") if p.strip()]),
                "ai_model": "deepseek-ai/deepseek-v4-flash"
            }
        }

    else:
        raise ValueError(f"Unsupported file format: {file_ext}")

# Backward compatibility alias
execute_document_pipeline = run_file_to_dashboard_pipeline
