"""
Centralized Backend Configuration & Environment Variables
"""

import os
from pathlib import Path

# Paths
BACKEND_DIR = Path(__file__).resolve().parent
ROOT_DIR = BACKEND_DIR.parent
DATA_DIR = ROOT_DIR / "data"
DEBUG_MD_DIR = DATA_DIR / "debug_md"
DEBUG_MD_DIR.mkdir(parents=True, exist_ok=True)

# File Processing Constraints
MAX_FILE_SIZE_BYTES = 16 * 1024 * 1024  # 16MB
MAX_OCR_PAGES = int(os.getenv("MAX_OCR_PAGES", "15"))
SPARSE_TEXT_THRESHOLD_CHARS = int(os.getenv("SPARSE_TEXT_THRESHOLD", "150"))

# OCR & Vision AI Models
DEFAULT_OCR_DPI = int(os.getenv("OCR_DPI", "350"))
MISTRAL_OCR_MODEL = os.getenv("MISTRAL_OCR_MODEL", "mistral-ocr-latest")
NVIDIA_TEXT_MODEL_NAME = os.getenv("NVIDIA_TEXT_MODEL", "meta/llama-3.1-70b-instruct")
DEFAULT_MIN_CONFIDENCE = float(os.getenv("MIN_OCR_CONFIDENCE", "0.50"))
MIN_PIXEL_GAP_THRESHOLD = 6.0
GAP_THRESHOLD_RATIO_DEFAULT = 0.8
ROW_Y_THRESHOLD_PX = 8.0

# Network & Server Settings
DEFAULT_PORT = int(os.getenv("PORT", "8000"))
DEFAULT_HOST = os.getenv("HOST", "0.0.0.0")
DEFAULT_ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")
