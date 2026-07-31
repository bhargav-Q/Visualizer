import base64
import mimetypes
import os
import io
import logging
from typing import Optional, Any
from dotenv import load_dotenv

logger = logging.getLogger(__name__)
load_dotenv()

# Initialize Mistral client
api_key = os.environ.get("MISTRAL_API_KEY")
_mistral_client = None

def get_mistral_client() -> Any:
    global _mistral_client
    if _mistral_client is None:
        key = os.environ.get("MISTRAL_API_KEY")
        if not key:
            raise ValueError("MISTRAL_API_KEY is missing from environment variables.")
        try:
            from mistralai.client import Mistral
            _mistral_client = Mistral(api_key=key)
        except ImportError:
            raise ImportError("The 'mistralai' package is not installed. Please run 'pip install mistralai'.")
    return _mistral_client

def encode_file_to_base64(file_path: str) -> str:
    """Encodes a local file to a Base64 string."""
    with open(file_path, "rb") as file:
        return base64.b64encode(file.read()).decode("utf-8")

def encode_bytes_to_base64(file_bytes: bytes) -> str:
    """Encodes raw byte buffer to a Base64 string."""
    return base64.b64encode(file_bytes).decode("utf-8")

def process_document_with_mistral_ocr(
    file_path: str = None,
    file_bytes: bytes = None,
    filename: str = None,
    output_md_path: str = None
) -> dict:
    """
    Processes PDF and Image files using official Mistral OCR API with Base64 Data URLs.
    Supports both disk file paths and in-memory byte buffers.
    """
    if file_path:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        filename = filename or os.path.basename(file_path)
        mime_type, _ = mimetypes.guess_type(file_path)
        base64_data = encode_file_to_base64(file_path)
    elif file_bytes is not None:
        filename = filename or "document.pdf"
        mime_type, _ = mimetypes.guess_type(filename)
        base64_data = encode_bytes_to_base64(file_bytes)
    else:
        raise ValueError("Either file_path or file_bytes must be provided.")

    if not mime_type:
        ext = filename.split(".")[-1].lower() if "." in filename else "pdf"
        mime_type = "application/pdf" if ext == "pdf" else f"image/{ext}"

    # Construct document payload per official documentation
    if mime_type == "application/pdf":
        document_payload = {
            "type": "document_url",
            "document_url": f"data:application/pdf;base64,{base64_data}",
        }
    else:
        document_payload = {
            "type": "image_url",
            "image_url": f"data:{mime_type};base64,{base64_data}",
        }

    client = get_mistral_client()

    # Execute OCR Request with zero-loss flags
    ocr_response = client.ocr.process(
        model="mistral-ocr-latest",
        document=document_payload,
        table_format="markdown",      # Preserves grid & borderless tables
        extract_header=True,          # Isolates page headers
        extract_footer=True,          # Isolates page footers/footnotes
        include_image_base64=True,     # Captures embedded figures
    )

    base_basename = os.path.splitext(os.path.basename(filename))[0]
    assets_dir = None
    if output_md_path:
        out_dir = os.path.dirname(os.path.abspath(output_md_path))
        assets_dir = os.path.join(out_dir, "assets", base_basename)
        os.makedirs(assets_dir, exist_ok=True)

    # Stitch page content into Markdown
    markdown_pages = []
    markdown_pages.append(f"# Extracted Document: {filename}\n")
    markdown_pages.append(
        f"*Total Pages Processed:* {len(ocr_response.pages)}\n\n---\n"
    )

    for page in ocr_response.pages:
        page_num = getattr(page, "index", 0) + 1
        markdown_pages.append(f"## Page {page_num}\n\n")

        if getattr(page, "header", None):
            markdown_pages.append(f"> **Header:** {page.header}\n\n")

        page_md = page.markdown or ""

        # 1. Resolve Table Placeholders ([tbl-x.md](tbl-x.md)) -> Expanded Markdown Grid Table
        page_tables = getattr(page, "tables", []) or []
        for tbl in page_tables:
            tbl_id = getattr(tbl, "id", None)
            tbl_content = getattr(tbl, "content", None)
            if tbl_id and tbl_content:
                placeholder1 = f"[{tbl_id}]({tbl_id})"
                placeholder2 = f"[{tbl_id}]"
                clean_content = f"\n\n{tbl_content.strip()}\n\n"
                if placeholder1 in page_md:
                    page_md = page_md.replace(placeholder1, clean_content)
                elif placeholder2 in page_md:
                    page_md = page_md.replace(placeholder2, clean_content)
                elif tbl_id in page_md:
                    page_md = page_md.replace(tbl_id, clean_content)

        # 2. Resolve Image Assets & Save Base64 to Disk
        page_images = getattr(page, "images", []) or []
        for img in page_images:
            img_id = getattr(img, "id", None)
            img_b64 = getattr(img, "image_base64", None)
            if img_id and img_b64:
                try:
                    raw_b64 = img_b64.split(",", 1)[1] if "," in img_b64 else img_b64
                    img_bytes = base64.b64decode(raw_b64)
                    
                    if assets_dir:
                        img_save_path = os.path.join(assets_dir, img_id)
                        with open(img_save_path, "wb") as f_img:
                            f_img.write(img_bytes)
                        rel_img_path = f"assets/{base_basename}/{img_id}"
                        old_link = f"![{img_id}]({img_id})"
                        new_link = f"![{img_id}]({rel_img_path})"
                        if old_link in page_md:
                            page_md = page_md.replace(old_link, new_link)
                except Exception as img_err:
                    logger.warning(f"Error saving OCR image {img_id}: {img_err}")

        markdown_pages.append(page_md)

        if getattr(page, "footer", None):
            markdown_pages.append(f"\n\n> **Footer:** {page.footer}\n")

        markdown_pages.append("\n\n---\n\n")

    full_md_text = "".join(markdown_pages)

    # Optionally write to file
    if output_md_path:
        os.makedirs(os.path.dirname(os.path.abspath(output_md_path)), exist_ok=True)
        with open(output_md_path, "w", encoding="utf-8") as md_file:
            md_file.write(full_md_text)

    return {
        "raw_response": ocr_response,
        "markdown_text": full_md_text,
        "page_count": len(ocr_response.pages),
    }
