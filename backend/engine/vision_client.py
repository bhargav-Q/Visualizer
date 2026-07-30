import os
import json
import base64
import time
import asyncio
import logging
import httpx
from dotenv import load_dotenv
from typing import Optional
from openai import OpenAI, AsyncOpenAI
from engine.pydantic_models import DocumentAnalytics
from config import VISION_API_TIMEOUT_SECONDS, CIRCUIT_BREAKER_COOLDOWN_SECONDS, MISTRAL_OCR_MODEL, BACKEND_DIR, ROOT_DIR

logger = logging.getLogger(__name__)

load_dotenv(dotenv_path=BACKEND_DIR / ".env")
load_dotenv(dotenv_path=ROOT_DIR / ".env")
load_dotenv()
api_key = os.getenv("NVIDIA_API_KEY")
mistral_api_key = os.getenv("MISTRAL_API_KEY")

VISION_MODEL_NAME = os.getenv("VISION_MODEL_NAME", "mistral-ocr-latest")

# Shared HTTPX resilient timeout configuration
TIMEOUT_CONFIG = httpx.Timeout(VISION_API_TIMEOUT_SECONDS, connect=5.0)

def get_mistral_client():
    """Returns initialized Mistral API client using MISTRAL_API_KEY."""
    key = os.getenv("MISTRAL_API_KEY")
    if not key:
        logger.warning("MISTRAL_API_KEY is missing from environment")
        return None
    try:
        try:
            from mistralai.client import Mistral
        except ImportError:
            from mistralai import Mistral
        return Mistral(api_key=key)
    except Exception as e:
        logger.warning(f"Failed to initialize Mistral client: {e}")
        return None

def process_document_with_mistral_ocr(document_url: str = None, document_bytes: bytes = None) -> Optional[str]:
    """
    Executes Mistral OCR (model: mistral-ocr-latest) on document URL or raw image bytes.
    Returns concatenated page markdown.
    """
    if is_vision_api_disabled():
        logger.warning("Vision API circuit breaker active. Skipping Mistral OCR request.")
        return None

    client = get_mistral_client()
    if not client:
        return None

    doc_payload = None
    if document_url:
        doc_payload = {"type": "document_url", "document_url": document_url}
    elif document_bytes:
        encoded = base64.b64encode(document_bytes).decode("utf-8")
        doc_payload = {"type": "image_url", "image_url": f"data:image/png;base64,{encoded}"}
    else:
        return None

    try:
        ocr_response = client.ocr.process(
            model=MISTRAL_OCR_MODEL,
            document=doc_payload
        )
        if ocr_response and hasattr(ocr_response, "pages") and ocr_response.pages:
            markdown_pages = [page.markdown for page in ocr_response.pages if hasattr(page, "markdown") and page.markdown]
            return "\n\n".join(markdown_pages)
    except Exception as e:
        logger.warning(f"Mistral OCR error: {e}")
        disable_vision_api(CIRCUIT_BREAKER_COOLDOWN_SECONDS)
        return None

# ==============================================================================
# NVIDIA NIM API CALLS (COMMENTED OUT FOR PURE MISTRAL OCR TESTING)
# UNCOMMENT THESE FUNCTIONS ONCE MISTRAL OCR VERIFICATION IS COMPLETE
# ==============================================================================

def get_nim_client() -> Optional[OpenAI]:
    """Returns an OpenAI client initialized with NVIDIA NIM base URL. [DISABLED FOR MISTRAL OCR TEST]"""
    # key = os.getenv("NVIDIA_API_KEY")
    # if not key:
    #     logger.warning("NVIDIA_API_KEY is missing from environment")
    #     return None
    # nim_url = os.getenv("NVIDIA_NIM_BASE_URL", "https://integrate.api.nvidia.com/v1")
    # return OpenAI(
    #     base_url=nim_url,
    #     api_key=key,
    #     http_client=httpx.Client(timeout=TIMEOUT_CONFIG),
    #     max_retries=1
    # )
    return None

def convert_image_to_markdown_mistral(png_bytes: bytes, page_num: int) -> str:
    """
    STAGE 1: Mistral OCR processes a single page PNG image into layout-accurate Markdown.
    Tags output with <!-- PAGE X START --> and <!-- PAGE X END -->.
    """
    client = get_mistral_client()
    if not client:
        return f"<!-- PAGE {page_num} START -->\n\nPage {page_num} content.\n\n<!-- PAGE {page_num} END -->"

    try:
        encoded_b64 = base64.b64encode(png_bytes).decode("utf-8")
        data_uri = f"data:image/png;base64,{encoded_b64}"

        ocr_response = client.ocr.process(
            model=MISTRAL_OCR_MODEL,
            document={
                "type": "image_url",
                "image_url": data_uri
            }
        )

        page_md = ocr_response.pages[0].markdown if (ocr_response and hasattr(ocr_response, "pages") and ocr_response.pages) else ""
        clean_md = page_md.strip() if page_md else f"Page {page_num} content."
        return f"<!-- PAGE {page_num} START -->\n\n{clean_md}\n\n<!-- PAGE {page_num} END -->"
    except Exception as exc:
        logger.warning(f"Mistral OCR Stage 1 error on page {page_num}: {exc}")
        return f"<!-- PAGE {page_num} START -->\n\nPage {page_num} content.\n\n<!-- PAGE {page_num} END -->"

def extract_analytics_and_summary_with_nim(aggregated_markdown: str) -> Optional[DocumentAnalytics]:
    """
    STAGE 2: Meta Llama 3.1 70B on NVIDIA NIM [TEMPORARILY DISABLED FOR MISTRAL OCR VERIFICATION].
    Uncomment body below to re-enable NVIDIA Llama text extraction.
    """
    # client = get_nim_client()
    # if not client:
    #     logger.warning("NIM client unavailable for Stage 2. Falling back.")
    #     return None
    # model_name = os.getenv("NVIDIA_TEXT_MODEL", "meta/llama-3.1-70b-instruct")
    # ... (NVIDIA Llama API Call preserved)
    return None

def get_async_openai_client() -> Optional[AsyncOpenAI]:
    """Returns an AsyncOpenAI client initialized with NVIDIA NIM base URL [DISABLED FOR MISTRAL OCR TEST]."""
    # if not api_key:
    #     return None
    # nim_url = os.getenv("NVIDIA_NIM_BASE_URL", "https://integrate.api.nvidia.com/v1")
    # return AsyncOpenAI(base_url=nim_url, api_key=api_key, http_client=httpx.AsyncClient(timeout=TIMEOUT_CONFIG), max_retries=1)
    return None

def encode_image_to_base64(image_bytes: bytes) -> str:
    """Encodes raw image bytes into a Base64 data URL string."""
    encoded = base64.b64encode(image_bytes).decode("utf-8")
    return f"data:image/png;base64,{encoded}"

_api_disabled_until = 0.0

def is_vision_api_disabled() -> bool:
    global _api_disabled_until
    return time.time() < _api_disabled_until

def disable_vision_api(seconds: float = CIRCUIT_BREAKER_COOLDOWN_SECONDS):
    global _api_disabled_until
    _api_disabled_until = time.time() + seconds
    logger.warning(f"NVIDIA API disabled globally for {seconds} seconds.")

def extract_analytics_with_vision(image_bytes: bytes, text_hint: str = "", max_retries: int = 3) -> Optional[DocumentAnalytics]:
    """
    Uses Mistral OCR (mistral-ocr-latest) to process image_bytes into layout-accurate Markdown text.
    NVIDIA Llama stage is bypassed while testing Mistral OCR.
    """
    if not image_bytes:
        return None

    # Step 1: Mistral OCR (Vision -> Markdown)
    try:
        md_text = convert_image_to_markdown_mistral(image_bytes, page_num=1)
    except Exception as exc:
        logger.warning(f"Mistral OCR error in extract_analytics_with_vision: {exc}")
        md_text = text_hint or ""

    if text_hint and text_hint.strip() not in md_text:
        md_text = f"{md_text}\n\nContext Hint:\n{text_hint}"

    if not md_text or not md_text.strip():
        logger.warning("Empty Markdown extracted from image. Returning None.")
        return None

    # Step 2: NVIDIA NIM Llama (Commented out during Mistral OCR testing phase)
    # return extract_analytics_and_summary_with_nim(md_text)
    return None

async def extract_analytics_with_vision_async(image_bytes: bytes, text_hint: str = "") -> Optional[DocumentAnalytics]:
    """
    Async non-blocking version of extract_analytics_with_vision.
    """
    try:
        return await asyncio.to_thread(extract_analytics_with_vision, image_bytes, text_hint, max_retries=1)
    except Exception as exc:
        logger.warning(f"Async Vision LLM call failed or timed out: {exc}")
        return None

