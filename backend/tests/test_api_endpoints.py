import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_health_check_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["status"] in ["ok", "active"]

def test_upload_tabular_csv_endpoint():
    csv_content = "Year,Revenue\n2023,1000\n2024,1500"
    files = {"file": ("sales_report.csv", csv_content, "text/csv")}
    response = client.post("/api/upload", files=files)
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["status"] == "success"
    assert json_data["file_name"] == "sales_report.csv"
    assert json_data["file_type"] == "csv"
    assert json_data["data_category"] == "tabular"

def test_upload_alias_v1_endpoint():
    csv_content = "Metric,Value\nUsers,5000\nActive,3200"
    files = {"file": ("user_stats.csv", csv_content, "text/csv")}
    response = client.post("/api/v1/upload", files=files)
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["status"] == "success"

def test_upload_invalid_file_type():
    files = {"file": ("malicious.exe", b"binary", "application/octet-stream")}
    response = client.post("/api/upload", files=files)
    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]
