from pathlib import Path

from fastapi.testclient import TestClient

from api.app import app


def test_pipeline_run_accepts_csv_and_returns_pipeline_result():
    sample_path = Path("data/sample_data/employees.csv")
    client = TestClient(app)

    with sample_path.open("rb") as dataset:
        response = client.post(
            "/pipeline/run",
            files={"file": ("employees.csv", dataset, "text/csv")},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "success"
    assert payload["run_id"]
    assert payload["schema"] is not None
    assert payload["initial_profile"]["row_count"] == 1030
    assert payload["initial_validation"]
    assert payload["healing"]
    assert payload["final_validation"]
    assert payload["quality_score"]["enabled"] is True
    assert payload["audit_trail"]["dataset"]["path"]
    assert Path(payload["output"]["cleaned_dataset"]).exists()