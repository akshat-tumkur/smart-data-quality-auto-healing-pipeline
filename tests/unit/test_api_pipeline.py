from copy import deepcopy
from pathlib import Path

from fastapi.testclient import TestClient

from api.app import app
from api.routes.pipeline import pipeline_service

def test_pipeline_run_rejects_unsupported_file_type():
    response = TestClient(app).post(
        "/pipeline/run",
        files={"file": ("employees.json", b"{}", "application/json")},
    )

    assert response.status_code == 415
    assert response.json()["detail"] == "Only CSV uploads are supported."

def test_pipeline_run_rejects_empty_upload():
    response = TestClient(app).post(
        "/pipeline/run",
        files={"file": ("empty.csv", b"", "text/csv")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "The uploaded dataset is empty."

def test_pipeline_run_returns_clear_schema_error(monkeypatch):
    original_config = pipeline_service.config
    test_config = deepcopy(original_config)
    test_config["schema"] = {
        "allow_extra_columns": True,
        "columns": {
            "required_but_missing": {"type": "string", "nullable": False},
        },
    }
    monkeypatch.setattr(pipeline_service, "config", test_config)

    response = TestClient(app).post(
        "/pipeline/run",
        files={"file": ("employees.csv", b"name\nAlice\n", "text/csv")},
    )

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["message"] == "The dataset is missing required schema columns."
    assert detail["result"]["schema"]["missing_columns"] == ["required_but_missing"]


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

    download_response = client.get(f"/pipeline/{payload['run_id']}/download")
    assert download_response.status_code == 200
    assert download_response.headers["content-type"].startswith("text/csv")
    assert download_response.content.startswith(b"employee_id,")


def test_download_returns_not_found_for_unknown_run():
    response = TestClient(app).get(
        "/pipeline/00000000000000000000000000000000/download"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Cleaned dataset was not found."