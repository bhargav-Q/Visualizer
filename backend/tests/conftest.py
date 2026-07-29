import pytest
from fastapi.testclient import TestClient
import sys
import os

import tempfile

import uuid
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["DUCKDB_PATH"] = ":memory:"

from main import app

@pytest.fixture(autouse=True)
def disable_external_apis(request):
    """Automatically disable external LLM network calls during unit test suite execution."""
    from engine.vision_client import disable_vision_api
    disable_vision_api(999999.0)
    yield
    disable_vision_api(999999.0)

@pytest.fixture
def client():
    return TestClient(app)
