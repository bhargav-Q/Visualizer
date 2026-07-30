import pytest
import config

def test_config_default_dpi():
    assert config.DEFAULT_OCR_DPI in [300, 350]

def test_config_paths():
    assert config.BACKEND_DIR.exists()
    assert config.DATA_DIR.exists()
    assert config.DEBUG_MD_DIR.exists()

def test_config_limits():
    assert config.MAX_FILE_SIZE_BYTES == 16 * 1024 * 1024
    assert config.MAX_OCR_PAGES >= 1
