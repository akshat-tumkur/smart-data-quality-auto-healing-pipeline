from unittest.mock import Mock, patch

import pytest

from frontend.services.api_client import (
    PipelineApiClient,
    PipelineApiError,
    friendly_error_message,
)


def test_health_uses_configured_base_url():
    response = Mock()
    response.json.return_value = {"status": "ok"}

    with patch("frontend.services.api_client.requests.get", return_value=response) as get:
        payload = PipelineApiClient("http://api.example/").get_health()

    assert payload == {"status": "ok"}
    get.assert_called_once_with("http://api.example/health", timeout=1.5)


def test_run_pipeline_posts_multipart_file_to_existing_endpoint():
    response = Mock()
    response.ok = True
    response.json.return_value = {"status": "success", "run_id": "abc123"}

    with patch("frontend.services.api_client.requests.post", return_value=response) as post:
        payload = PipelineApiClient("http://api.example").run_pipeline(
            "employees.csv",
            b"employee_id\n1\n",
        )

    assert payload["run_id"] == "abc123"
    post.assert_called_once_with(
        "http://api.example/pipeline/run",
        files={"file": ("employees.csv", b"employee_id\n1\n", "text/csv")},
        timeout=300,
    )


def test_schema_error_preserves_structured_pipeline_result():
    response = Mock()
    response.ok = False
    response.status_code = 422
    response.json.return_value = {
        "detail": {
            "message": "The dataset is missing required schema columns.",
            "result": {"status": "schema_failed", "schema": {"missing_columns": ["id"]}},
        }
    }

    with patch("frontend.services.api_client.requests.post", return_value=response):
        with pytest.raises(PipelineApiError) as error:
            PipelineApiClient().run_pipeline("dataset.csv", b"value\n1\n")

    assert error.value.status_code == 422
    assert error.value.schema_failure_result == {
        "status": "schema_failed",
        "schema": {"missing_columns": ["id"]},
    }


def test_cleaned_dataset_url_uses_run_id_returned_by_api():
    run_id = "0123456789abcdef0123456789abcdef"

    url = PipelineApiClient("http://api.example/").cleaned_dataset_url(run_id)

    assert url == f"http://api.example/pipeline/{run_id}/download"


def test_cleaned_dataset_url_rejects_invalid_run_id():
    with pytest.raises(ValueError, match="invalid run ID"):
        PipelineApiClient().cleaned_dataset_url("../../cleaned.csv")


@pytest.mark.parametrize(
    ("status_code", "detail", "expected"),
    [
        (400, "invalid CSV", "Could not process this dataset. Please verify that the file is valid."),
        (415, "Only CSV uploads are supported.", "Unsupported file type. Please upload a CSV."),
        (422, {"message": "The required id column is missing."}, "The required id column is missing."),
        (500, "internal details are hidden", "Pipeline execution failed. Please try again."),
        (404, "Cleaned dataset was not found.", "The cleaned dataset is unavailable. Run the pipeline again."),
    ],
)
def test_api_errors_have_user_friendly_messages(status_code, detail, expected):
    assert friendly_error_message(PipelineApiError(status_code, detail)) == expected
