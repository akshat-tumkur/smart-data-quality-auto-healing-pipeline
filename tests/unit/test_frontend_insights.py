from frontend.result_views import (
    build_audit_timeline,
    build_healing_insights,
    build_issue_comparison,
    build_quality_insights,
    build_remaining_issues,
    build_validation_insights,
)


def sample_result():
    return {
        "quality_score": {
            "enabled": True,
            "initial": {"score": 77.0183, "components": {"completeness": 80, "validity": 70, "uniqueness": 90}},
            "final": {"score": 94.1349, "components": {"completeness": 100, "validity": 82, "uniqueness": 95}},
            "delta": 17.1166,
        },
        "metrics": {
            "missing_values": {"before": 332, "after": 0, "delta": -332},
            "duplicate_affected_rows": {"before": 14, "after": 12, "delta": -2},
        },
        "initial_validation": [
            {"validator_name": "Null Validator", "status": False, "rows_affected": 332, "metadata": {}},
            {"validator_name": "Data Type Validator", "status": False, "rows_affected": 29, "metadata": {"column": "salary"}},
            {"validator_name": "Regex Validator", "status": False, "rows_affected": 92, "metadata": {"column": "email"}},
        ],
        "final_validation": [
            {"validator_name": "Null Validator", "status": True, "rows_affected": 0, "metadata": {}},
            {"validator_name": "Data Type Validator", "status": True, "rows_affected": 0, "metadata": {"column": "salary"}},
            {"validator_name": "Regex Validator", "status": False, "rows_affected": 92, "metadata": {"column": "email"}},
        ],
        "healing": [
            {"healer_name": "Datatype Healer", "status": "success", "rows_affected": 1, "metadata": {"attempted": 29, "repaired": 29, "remaining": 0}},
            {"healer_name": "Regex Healer", "status": "partial", "rows_affected": 2, "metadata": {"attempted": 92, "repaired": 0, "remaining": 92}},
        ],
        "schema": {"status": True},
        "anomaly_detection": None,
        "audit_trail": {"dataset": {"processed_at": "2026-10-07T10:00:00Z"}},
    }


def test_quality_insights_extract_score_delta_and_components():
    insights = build_quality_insights(sample_result()["quality_score"])

    assert insights["before"] == 77.0183
    assert insights["after"] == 94.1349
    assert insights["improvement"] == 17.1166
    assert insights["components"]["validity"] == {"before": 70, "after": 82}


def test_issue_and_remaining_insights_use_backend_values():
    result = sample_result()

    issues = build_issue_comparison(result)
    remaining = build_remaining_issues(result)

    assert {item["label"] for item in issues} == {"Missing values", "Duplicate affected rows", "Datatype: salary", "Invalid formatting: email"}
    assert {item["label"]: item["status"] for item in remaining}["Missing values"] == "Resolved"
    assert {item["label"]: item["status"] for item in remaining}["Invalid formatting: email"] == "Unresolved"


def test_healing_and_validation_insights_preserve_partial_status():
    result = sample_result()

    healing = build_healing_insights(result["healing"])
    validation = build_validation_insights(result)

    assert healing[1]["status"] == "partial"
    assert healing[1]["remaining"] == 92
    assert any(row["validation"] == "Invalid formatting: email" and row["remaining"] == 92 for row in validation)


def test_timeline_handles_disabled_anomaly_detection():
    timeline = build_audit_timeline(sample_result())

    assert any(event["step"] == "Anomaly detection" and event["detail"] == "Disabled" for event in timeline)
    assert any(event["step"] == "Auto-healing" and "1 partial" in event["detail"] for event in timeline)