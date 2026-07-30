import pytest
from services.main_pipeline import run_file_to_dashboard_pipeline

def test_pipeline_tabular_integration():
    csv_bytes = b"Category,Amount\nSales,500\nMarketing,200\nOperations,150"
    res = run_file_to_dashboard_pipeline(file_bytes=csv_bytes, filename="company_budget.csv")
    
    assert res["status"] == "success"
    assert res["source_type"] == "tabular"
    assert res["file_name"] == "company_budget.csv"
    assert res["file_type"] == "csv"
    assert res["data_category"] == "tabular"
    assert isinstance(res["kpis"], list)
    assert isinstance(res["charts"], list)
    assert "raw_markdown" in res

def test_pipeline_unsupported_format():
    with pytest.raises(ValueError):
        run_file_to_dashboard_pipeline(file_bytes=b"dummy", filename="unsupported.exe")
