from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest


APP_PATH = Path(__file__).resolve().parents[2] / "frontend" / "app.py"


def run_dashboard_with_result(result: dict, *, error: str | None = None) -> AppTest:
    with patch("frontend.services.api_client.requests.get") as health_request:
        health_request.return_value.json.return_value = {"status": "ok"}
        health_request.return_value.raise_for_status.return_value = None
        app = AppTest.from_file(APP_PATH)
        app.session_state["pipeline_result"] = result
        app.session_state["pipeline_error"] = error
        app.session_state["run_id"] = result.get("run_id")
        app.run(timeout=15)
    return app


def test_dashboard_renders_scores_metrics_schema_and_validation_from_result():
    result = {
        "status": "success",
        "run_id": "0123456789abcdef0123456789abcdef",
        "quality_score": {
            "enabled": True,
            "initial": {
                "score": 74.0,
                "components": {"completeness": 80.0, "validity": 70.0, "uniqueness": 72.0},
            },
            "final": {
                "score": 91.0,
                "components": {"completeness": 100.0, "validity": 90.0, "uniqueness": 80.0},
            },
            "delta": 17.0,
        },
        "metrics": {
            "missing_values": {"before": 10, "after": 0, "delta": -10},
            "duplicates": {"before": 3, "after": 1, "delta": -2},
            "rows": {"before": 50, "after": 50, "delta": 0},
        },
        "schema": {
            "status": True,
            "message": "Schema validation passed.",
            "missing_columns": [],
            "unexpected_columns": [],
            "datatype_mismatches": {},
            "nullable_violations": {},
            "metadata": {"allow_extra_columns": True},
        },
        "initial_validation": [
            {"validator_name": "NullValidator", "status": False, "rows_affected": 10, "message": "Nulls found"}
        ],
        "final_validation": [
            {"validator_name": "NullValidator", "status": True, "rows_affected": 0, "message": "No nulls"}
        ],
        "healing": [
            {
                "healer_name": "MissingValueHealer",
                "status": "success",
                "message": "Filled missing values using the configured strategy.",
                "rows_affected": 10,
                "metadata": {"strategy": "median"},
            }
        ],
        "anomaly_detection": {
            "enabled": True,
            "status": "completed",
            "detector_name": "IsolationForestDetector",
            "anomaly_count": 1,
            "anomaly_indices": [7],
            "feature_columns": ["salary"],
        },
        "execution_time": 0.42,
        "audit_trail": {
            "dataset": {
                "path": "C:/private/staging/upload.csv",
                "processed_at": "2026-09-28T10:00:00+00:00",
            },
            "validation": {"initial": [], "final": []},
            "healing_actions": [],
            "execution_time": 0.42,
        },
    }

    app = run_dashboard_with_result(result)

    assert not app.exception
    metric_values = [metric.value for metric in app.metric]
    assert "74.00" in metric_values
    assert "91.00" in metric_values
    assert "80.00 → 100.00" in metric_values
    assert "10 → 0" in metric_values
    assert ("Anomalies detected", "1") in [(metric.label, metric.value) for metric in app.metric]
    assert ("Healers executed", "1") in [(metric.label, metric.value) for metric in app.metric]
    assert any("NullValidator" in element.value for element in app.markdown)
    assert any("MissingValueHealer" in element.value for element in app.markdown)
    assert "Detected anomalies are flagged for review and are not automatically healed." in [
        item.value for item in app.info
    ]
    assert "View structured audit details" in [item.label for item in app.expander]
    assert "C:/private/staging/upload.csv" not in str(app.json)
    assert "Schema checks passed." in [item.value for item in app.success]


def test_dashboard_renders_schema_failure_without_inventing_validation_results():
    result = {
        "status": "schema_failed",
        "run_id": "0123456789abcdef0123456789abcdef",
        "schema": {
            "status": False,
            "message": "Missing required columns: customer_id.",
            "missing_columns": ["customer_id"],
            "unexpected_columns": [],
            "datatype_mismatches": {},
            "nullable_violations": {},
            "metadata": {"allow_extra_columns": True},
        },
        "quality_score": {"enabled": False},
        "metrics": {},
        "initial_validation": [],
        "final_validation": [],
        "healing": [],
        "anomaly_detection": None,
        "audit_trail": {
            "dataset": {"path": "C:/private/staging/bad.csv", "processed_at": "2026-09-28T10:00:00+00:00"},
            "validation": {"initial": [], "final": []},
            "healing_actions": [],
        },
    }

    app = run_dashboard_with_result(
        result,
        error="The dataset is missing required schema columns.",
    )

    assert not app.exception
    assert "The dataset is missing required schema columns." in [item.value for item in app.error]
    assert "The pipeline stopped because required schema columns are missing." in [
        item.value for item in app.warning
    ]
    assert "Validation did not run because required schema columns were missing." in [
        item.value for item in app.info
    ]
    assert "Auto-healing did not run because required schema columns were missing." in [
        item.value for item in app.info
    ]
    assert "Anomaly detection did not run because required schema columns were missing." in [
        item.value for item in app.info
    ]


def test_dashboard_labels_anomaly_detection_disabled_on_successful_run():
    result = {
        "status": "success",
        "anomaly_detection": None,
        "healing": [],
        "quality_score": {"enabled": False},
        "metrics": {},
        "schema": {"status": True, "message": "Schema validation passed."},
        "initial_validation": [],
        "final_validation": [],
        "audit_trail": {"dataset": {}, "validation": {"initial": [], "final": []}},
    }

    app = run_dashboard_with_result(result)

    assert not app.exception
    assert "Anomaly detection disabled for this run." in [item.value for item in app.info]
    assert "No automatic repairs were required." in [item.value for item in app.info]
