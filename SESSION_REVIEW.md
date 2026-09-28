# Session Review: Adaptive Data Quality Platform Frontend

This note summarizes the repository inspection, implementation work, decisions, and verification performed in this session. It is intended for review and does not replace the project README.

## Repository findings before implementation

- The repository contains a Python backend under `src/`, with FastAPI routes, pipeline orchestration, configuration-driven schema and validators, profiling, healing, optional anomaly detection, quality scoring, audit generation, and report generation.
- A Streamlit file already existed at `frontend/app.py`. It contained placeholder dashboard values and a non-integrated upload flow. There was no React/Vite frontend.
- The API implementation is in `src/api/`; pipeline assembly and serialization are in `src/api/services/pipeline_service.py`, `src/core/pipeline.py`, and `src/core/pipeline_result.py`.
- `GET /health` returns `{"status":"ok"}`.
- `POST /pipeline/run` accepts a multipart upload in the `file` field. A successful response includes `PipelineResult.to_dict()` fields plus `status`, `run_id`, and `output` metadata.
- `GET /pipeline/{run_id}/download` returns the cleaned CSV as an attachment. The API generates a 32-character UUID hex run ID.
- FastAPI has no CORS middleware. The Streamlit health and run calls are server-to-server; the cleaned file is linked directly to the API endpoint, so no CORS change was needed.
- The pipeline stops early when required schema columns are missing. The API returns HTTP 422 with a structured `detail` object containing a message and result. In that path validation, anomaly detection, and healing have not run.
- When anomaly detection is disabled, the normal result contains `anomaly_detection: null`.

## Milestones completed

### G — Dashboard shell

- Replaced the placeholder dashboard with a restrained Streamlit dashboard shell for the Adaptive Data Quality Platform.
- Added an upload area, pipeline overview, sidebar run context, and empty result state.
- Removed all hardcoded demo metrics and charts.

### H — API integration

- Added a small API client that centralizes the API base URL and calls `/health` and `/pipeline/run`.
- Added multipart CSV upload, API connection status, loading state, friendly upload/pipeline errors, and Streamlit session state for returned results.
- Preserved the backend's structured schema-failure result from HTTP 422 for rendering in the dashboard.

### I — Score, metrics, schema, and validation views

- Added API-driven before/after quality scores and component scores.
- Added only the before/after metrics returned by the API.
- Added schema status and findings for missing/unexpected columns, datatype mismatches, and nullable violations.
- Added validation result tables for before and after healing.
- Kept the schema-failure state accurate: validation is shown as not run when the backend short-circuits on missing required columns.

### J — Healing, anomaly, and audit views

- Added healing action summaries with healer name, status, affected rows, messages, and expandable metadata.
- Added anomaly count, detector, row indices, and feature columns when returned. The UI distinguishes disabled detection from detection skipped due to schema failure and states that anomalies are flagged for review, not auto-healed.
- Added audit and run information, including run ID, uploaded filename, processing timestamp, execution time, validation/healer counts, quality score change, and expandable structured audit data.
- Omitted internal filesystem paths from the audit view.

### K — Download, errors, responsive polish, and documentation

- Added a cleaned CSV download link built from the run ID returned by the backend. The backend's attachment response controls the downloaded filename; the dashboard does not construct a filesystem path.
- Added user-facing mappings for HTTP 400, 404, 415, 422, and 500 responses. The 500 message does not expose server internals.
- Added responsive table/layout styling and reset prior results when the selected filename or size changes.
- Replaced the scaffold README with setup, startup, workflow, environment, and endpoint documentation.
- Added `uvicorn` to `requirements.txt` so a fresh install can run the documented FastAPI command.

### Integration verification (2026-09-28)

- Created a clean `.venv` with Python **3.11.9**, matching the NumPy wheel compatibility available for this project. Installed all project dependencies successfully; `pip check` reported no broken requirements.
- Added `httpx2` because the currently resolved Starlette 1.7.0 TestClient requires it. Added `pandas<3` because Pandas 3 changed object string dtype behavior and broke an existing schema datatype assertion; Pandas 2.3.3 restores the expected behavior.
- Full backend suite: **48 passed**. Frontend suite: **13 passed**.
- FastAPI and Streamlit both started successfully. A Streamlit AppTest uploaded `data/sample_data/employees.csv`, ran the real pipeline through FastAPI, and rendered the returned `PipelineResult`. The dashboard showed quality score 77.02 → 93.69 and before/after metrics, validation, healing, anomaly, and audit sections.
- The download link used the run ID returned by that live pipeline request. Fetching it from FastAPI returned HTTP 200 and a 176,438-byte CSV attachment.
- A CSV missing required schema columns returned HTTP 422; the dashboard showed the schema error and correctly indicated that validation, healing, and anomaly detection had not run.
- Server logs showed the expected health 200, pipeline 200, download 200, and schema-failure 422 responses, with no server errors. `git diff --check` and Python compilation passed.
- The test suite emitted two existing Pandas deprecation warnings from `src/auto_healing/healers/regex_healer.py:55` (`is_categorical_dtype`).
- A physical browser launch was attempted but blocked by environment policy. The frontend round trip and download were verified with Streamlit AppTest and an actual GET to FastAPI; browser console logs and a physical click were not verified.

## Implementation decisions

- Kept Streamlit because it was the repository's existing frontend framework. No React/Vite rewrite or charting/component dependency was introduced.
- Kept pipeline logic in the backend; frontend sections only render API values.
- Centralized API configuration in `API_BASE_URL`, with a local default of `http://localhost:8000`.
- Used a direct download link to the API so FastAPI serves its own CSV attachment. The configured API URL must be reachable from the user's browser for this link to work.
- Rendered API-provided table text with HTML escaping and excluded server filesystem paths from the audit display.
- No pipeline/backend implementation files were changed. Dependency changes are limited to Uvicorn for the documented API server command, `httpx2` for the resolved Starlette TestClient, and `pandas<3` to preserve existing dtype expectations in the backend suite.

## Files changed

- `frontend/app.py` — dashboard shell, health check, upload/run flow, results assembly, and download link.
- `frontend/result_views.py` — score, metrics, schema, validation, healing, anomaly, and audit sections.
- `frontend/services/__init__.py` — frontend service package marker.
- `frontend/services/api_client.py` — API URL, health/run calls, download URL validation, and friendly HTTP error messages.
- `tests/unit/test_frontend_api_client.py` — API client, URL, structured 422, and error-message tests.
- `tests/unit/test_frontend_result_views.py` — Streamlit rendering tests for successful and schema-failed runs, disabled anomalies, and audit path omission.
- `README.md` — setup and usage guide.
- `requirements.txt` — Uvicorn runtime dependency and compatible httpx2/Pandas constraints.

## Verification and limits

- Full backend suite: **48 passed**; frontend suite: **13 passed**.
- Python compilation, dependency consistency (`pip check`), and `git diff --check`: passed.
- Live upload, pipeline rendering, cleaned CSV download, and missing-schema failure were verified against running FastAPI and Streamlit processes as described above.
- The earlier Python 3.14/NumPy CPython 3.11 binary mismatch was resolved by using the clean Python 3.11.9 environment. The incompatible/missing TestClient dependency was resolved with `httpx2`.

## Current review status

Frontend milestones G through K and integration verification are complete. The only outstanding verification limit is the physical browser launch, which environment policy blocked; Streamlit AppTest and direct FastAPI requests covered the live workflow.
