"""Small HTTP client for the existing FastAPI pipeline endpoints."""

from __future__ import annotations

import os
import re
from typing import Any
from urllib.parse import quote

import requests


DEFAULT_API_BASE_URL = "http://localhost:8000"


class PipelineApiError(Exception):
    """An HTTP error returned by the pipeline API."""

    def __init__(self, status_code: int, detail: Any) -> None:
        super().__init__(f"Pipeline API returned HTTP {status_code}")
        self.status_code = status_code
        self.detail = detail

    @property
    def schema_failure_result(self) -> dict[str, Any] | None:
        if not isinstance(self.detail, dict):
            return None
        result = self.detail.get("result")
        return result if isinstance(result, dict) else None


def friendly_error_message(error: PipelineApiError) -> str:
    """Map API status codes to concise messages suitable for the dashboard."""

    if error.status_code == 400:
        return "Could not process this dataset. Please verify that the file is valid."
    if error.status_code == 404:
        return "The cleaned dataset is unavailable. Run the pipeline again."
    if error.status_code == 415:
        return "Unsupported file type. Please upload a CSV."
    if error.status_code == 422:
        if isinstance(error.detail, dict) and error.detail.get("message"):
            return str(error.detail["message"])
        return "Schema validation failed. Required columns are missing."
    if error.status_code == 500:
        return "Pipeline execution failed. Please try again."
    return f"The API could not process this request (HTTP {error.status_code})."


class PipelineApiClient:
    """Call the health, run, and download endpoints on one configured API."""

    def __init__(self, base_url: str | None = None) -> None:
        configured_url = base_url or os.getenv("API_BASE_URL", DEFAULT_API_BASE_URL)
        self.base_url = configured_url.rstrip("/")

    def get_health(self, timeout: float = 1.5) -> dict[str, Any]:
        response = requests.get(f"{self.base_url}/health", timeout=timeout)
        response.raise_for_status()
        payload = self._json_object(response)
        return payload

    def run_pipeline(
        self,
        filename: str,
        content: bytes,
        timeout: float = 300,
    ) -> dict[str, Any]:
        response = requests.post(
            f"{self.base_url}/pipeline/run",
            files={"file": (filename, content, "text/csv")},
            timeout=timeout,
        )
        if not response.ok:
            detail = self._error_detail(response)
            raise PipelineApiError(response.status_code, detail)
        return self._json_object(response)

    def cleaned_dataset_url(self, run_id: str) -> str:
        """Build the API download URL for an ID returned by a completed run."""

        if not isinstance(run_id, str) or not re.fullmatch(r"[0-9a-fA-F]{32}", run_id):
            raise ValueError("The pipeline API returned an invalid run ID.")
        return f"{self.base_url}/pipeline/{quote(run_id, safe='')}/download"

    @staticmethod
    def _json_object(response: requests.Response) -> dict[str, Any]:
        try:
            payload = response.json()
        except requests.exceptions.JSONDecodeError as exc:
            raise ValueError("The API returned an invalid JSON response.") from exc
        if not isinstance(payload, dict):
            raise ValueError("The API response must be a JSON object.")
        return payload

    @classmethod
    def _error_detail(cls, response: requests.Response) -> Any:
        try:
            payload = response.json()
        except requests.exceptions.JSONDecodeError:
            return None
        if isinstance(payload, dict):
            return payload.get("detail")
        return None
