"""Render API-backed quality, metric, schema, and validation sections."""

from __future__ import annotations

from html import escape
import re
from typing import Any

import streamlit as st
import plotly.graph_objects as go


STATUS_COLORS = {
    "success": "#218739",
    "partial": "#c47b00",
    "failed": "#c53d3d",
    "resolved": "#218739",
    "partially resolved": "#c47b00",
    "unresolved": "#c53d3d",
}


def build_quality_insights(quality_score: Any) -> dict[str, Any]:
    if not isinstance(quality_score, dict) or not quality_score.get("enabled"):
        return {"enabled": False}
    initial = quality_score.get("initial") or {}
    final = quality_score.get("final") or {}
    initial_components = initial.get("components") or {}
    final_components = final.get("components") or {}
    components = {
        name: {
            "before": initial_components[name],
            "after": final_components[name],
        }
        for name in initial_components
        if name in final_components
    }
    return {
        "enabled": True,
        "before": initial.get("score"),
        "after": final.get("score"),
        "improvement": quality_score.get("delta"),
        "components": components,
    }


def build_issue_comparison(result: dict[str, Any]) -> list[dict[str, Any]]:
    metrics = result.get("metrics") if isinstance(result, dict) else {}
    issues: list[dict[str, Any]] = []
    for key, label in (
        ("missing_values", "Missing values"),
        ("duplicate_affected_rows", "Duplicate affected rows"),
    ):
        values = metrics.get(key) if isinstance(metrics, dict) else None
        if isinstance(values, dict) and "before" in values and "after" in values:
            issues.append(_issue(label, values["before"], values["after"]))

    initial = _validation_index(result.get("initial_validation"))
    final = _validation_index(result.get("final_validation"))
    for key, (label, before) in initial.items():
        if key[0] in {"null", "duplicate"}:
            continue
        if key in final:
            issues.append(_issue(label, before, final[key][1]))
    return issues


def build_issue_reduction(result: dict[str, Any]) -> list[dict[str, Any]]:
    """Return reduction percentages for the same issues used by the comparison chart."""

    reductions = []
    for issue in build_issue_comparison(result):
        before = issue["before"]
        after = issue["after"]
        reductions.append(
            {
                **issue,
                "reduction_percent": _reduction_percent(before, after),
            }
        )
    return reductions


def build_attention_insights(result: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract unresolved final validation findings, sorted by remaining count."""

    initial = _validation_index(result.get("initial_validation"))
    final = _validation_index(result.get("final_validation"))
    attention: list[dict[str, Any]] = []
    for key, (label, remaining) in final.items():
        if not isinstance(remaining, (int, float)) or remaining <= 0:
            continue
        before = initial.get(key, (label, remaining))[1]
        status = "Partially resolved" if remaining < before else "Unresolved"
        attention.append(
            {
                "label": label,
                "remaining": remaining,
                "status": status,
                "metric": "validation affected rows",
            }
        )

    duplicate_metric = (result.get("metrics") or {}).get("duplicate_affected_rows", {})
    if (
        isinstance(duplicate_metric, dict)
        and duplicate_metric.get("after", 0) > 0
        and not any(item["label"] == "Duplicate records" for item in attention)
    ):
        before = duplicate_metric.get("before", duplicate_metric["after"])
        after = duplicate_metric["after"]
        attention.append(
            {
                "label": "Duplicate records",
                "remaining": after,
                "status": "Partially resolved" if after < before else "Unresolved",
                "metric": "duplicate affected rows",
            }
        )

    return sorted(attention, key=lambda item: item["remaining"], reverse=True)


def build_highest_priority_issue(result: dict[str, Any]) -> dict[str, Any] | None:
    attention = build_attention_insights(result)
    return attention[0] if attention else None


def render_insights(result: dict[str, Any]) -> None:
    """Render the human-readable dashboard interpretation of pipeline metadata."""

    schema_failed = result.get("status") == "schema_failed"
    quality = build_quality_insights(result.get("quality_score"))
    st.header("Data Quality Overview")
    if quality.get("enabled"):
        score_columns = st.columns(3)
        score_columns[0].metric("Before", _score_value(quality.get("before")))
        score_columns[1].metric("After", _score_value(quality.get("after")))
        score_columns[2].metric("Improvement", _score_delta(quality.get("improvement")))
        component_rows = [
            [
                _label(name),
                _score_value(values["before"]),
                _score_value(values["after"]),
            ]
            for name, values in quality.get("components", {}).items()
        ]
        if component_rows:
            _render_table(("Dimension", "Before", "After"), component_rows)
            st.plotly_chart(_component_chart(quality["components"]), use_container_width=True)
    else:
        st.info("Quality scoring is disabled for this run.")

    issues = build_issue_comparison(result)
    st.subheader("Issues Before vs After")
    if issues:
        st.plotly_chart(_issue_chart(issues), use_container_width=True)
    else:
        st.info("No comparable issue metrics were returned.")

    reductions = build_issue_reduction(result)
    st.subheader("Issue Reduction")
    if reductions:
        _render_table(
            ("Issue", "Reduction", "Before", "After"),
            [
                (
                    item["label"],
                    f"{item['reduction_percent']:.1f}%",
                    _format_value(item["before"]),
                    _format_value(item["after"]),
                )
                for item in reductions
            ],
        )
        st.plotly_chart(_reduction_chart(reductions), use_container_width=True)
    else:
        st.info("No issue reduction data was returned.")

    healing = build_healing_insights(result.get("healing"))
    st.subheader("Healing Effectiveness")
    if healing:
        _render_table(
            ("Healer", "Status", "Attempted", "Repaired", "Remaining"),
            [
                (
                    item["name"],
                    item["status"].upper(),
                    _format_value(item["attempted"]),
                    _format_value(item["repaired"]),
                    _format_value(item["remaining"]),
                )
                for item in healing
            ],
        )
        st.plotly_chart(_healing_chart(healing), use_container_width=True)
    else:
        st.info(
            "Auto-healing did not run because required schema columns were missing."
            if schema_failed
            else "No automatic repairs were required."
        )

    remaining = build_remaining_issues(result)
    st.subheader("Remaining Data Quality Issues")
    if remaining:
        groups = {"Resolved": [], "Partially resolved": [], "Unresolved": []}
        for issue in remaining:
            groups[issue["status"]].append(
                f"{issue['label']}: {issue['before']} → {issue['after']}"
            )
        for title, entries in groups.items():
            with st.expander(f"{title} ({len(entries)})", expanded=title != "Resolved"):
                if entries:
                    for entry in entries:
                        st.write(entry)
                else:
                    st.caption("None")
    else:
        st.info("No remaining issue comparison was available.")

    attention = build_attention_insights(result)
    st.subheader("What Needs Attention?")
    if attention:
        priority = attention[0]
        st.warning(
            f"Highest priority: {priority['label']} — "
            f"{_format_value(priority['remaining'])} {priority['metric']} remain."
        )
        _render_table(
            ("Issue", "Remaining", "State"),
            [
                (item["label"], _format_value(item["remaining"]), item["status"])
                for item in attention
            ],
        )
    elif result.get("status") != "schema_failed":
        st.success("No remaining data quality issues.")
    else:
        st.info("Attention findings are unavailable because schema validation stopped the run.")

    st.subheader("Validation Health")
    validation = build_validation_insights(result)
    if validation:
        _render_table(
            ("Validation", "Before", "After", "Remaining", "Status"),
            [
                (
                    row["validation"],
                    _format_value(row["before"]),
                    _format_value(row["after"]),
                    _format_value(row["remaining"]),
                    row["status"],
                )
                for row in validation
            ],
        )
    else:
        st.info(
            "Validation did not run because required schema columns were missing."
            if schema_failed
            else "No validation results were returned."
        )

    st.subheader("Audit Timeline")
    for index, event in enumerate(build_audit_timeline(result), start=1):
        st.markdown(f"**{index}. {event['step']}**  ")
        st.caption(event["detail"])


def _component_chart(components: dict[str, Any]) -> go.Figure:
    names = [_label(name) for name in components]
    figure = go.Figure()
    figure.add_bar(name="Before", x=names, y=[item["before"] for item in components.values()])
    figure.add_bar(name="After", x=names, y=[item["after"] for item in components.values()])
    figure.update_layout(barmode="group", yaxis_title="Score", yaxis_range=[0, 100], height=320)
    return figure


def _issue_chart(issues: list[dict[str, Any]]) -> go.Figure:
    figure = go.Figure()
    figure.add_bar(name="Before", x=[item["label"] for item in issues], y=[item["before"] for item in issues])
    figure.add_bar(name="After", x=[item["label"] for item in issues], y=[item["after"] for item in issues])
    figure.update_layout(barmode="group", yaxis_title="Affected rows", height=360)
    return figure


def _reduction_chart(reductions: list[dict[str, Any]]) -> go.Figure:
    figure = go.Figure(
        go.Bar(
            x=[item["reduction_percent"] for item in reductions],
            y=[item["label"] for item in reductions],
            orientation="h",
            marker_color="#218739",
        )
    )
    figure.update_layout(xaxis_title="Issue reduction (%)", xaxis_range=[0, 100], height=320)
    return figure


def _healing_chart(healing: list[dict[str, Any]]) -> go.Figure:
    labels = [item["name"] for item in healing]
    figure = go.Figure()
    figure.add_bar(name="Repaired", y=labels, x=[item["repaired"] if _is_number(item["repaired"]) else 0 for item in healing], orientation="h")
    figure.add_bar(name="Remaining", y=labels, x=[item["remaining"] if _is_number(item["remaining"]) else 0 for item in healing], orientation="h")
    figure.update_layout(barmode="group", xaxis_title="Rows / values", height=320)
    return figure


def build_healing_insights(healing: Any) -> list[dict[str, Any]]:
    if not isinstance(healing, list):
        return []
    insights = []
    for action in healing:
        if not isinstance(action, dict):
            continue
        metadata = action.get("metadata") if isinstance(action.get("metadata"), dict) else {}
        status = str(action.get("status", "unknown")).lower()
        insights.append(
            {
                "name": _friendly_healer_name(action.get("healer_name")),
                "status": status,
                "attempted": metadata.get("attempted", "Not available"),
                "repaired": metadata.get("repaired", metadata.get("changed", "Not available")),
                "remaining": metadata.get("remaining", metadata.get("unresolved", "Not available")),
                "rows_affected": action.get("rows_affected", "Not available"),
            }
        )
    return insights


def build_remaining_issues(result: dict[str, Any]) -> list[dict[str, Any]]:
    issues = build_issue_comparison(result)
    remaining = []
    for issue in issues:
        before = issue["before"]
        after = issue["after"]
        if after == 0:
            status = "Resolved"
        elif isinstance(before, (int, float)) and after < before:
            status = "Partially resolved"
        else:
            status = "Unresolved"
        remaining.append({**issue, "status": status})
    return remaining


def build_validation_insights(result: dict[str, Any]) -> list[dict[str, Any]]:
    initial = _validation_index(result.get("initial_validation"))
    final = _validation_index(result.get("final_validation"))
    rows = []
    for key, (label, before) in initial.items():
        after = final.get(key, (label, 0))[1]
        rows.append(
            {
                "validation": label,
                "before": before,
                "after": after,
                "remaining": after,
                "status": "Passed" if after == 0 else "Needs attention",
            }
        )
    return rows


def build_audit_timeline(result: dict[str, Any]) -> list[dict[str, str]]:
    healing = build_healing_insights(result.get("healing"))
    partial = sum(item["status"] == "partial" for item in healing)
    repaired = sum(
        item["repaired"] for item in healing if isinstance(item["repaired"], (int, float))
    )
    return [
        {"step": "Dataset ingested", "detail": result.get("audit_trail", {}).get("dataset", {}).get("processed_at", "Completed")},
        {"step": "Schema validated", "detail": _schema_status(result.get("schema"))},
        {"step": "Initial profiling and validation", "detail": f"{len(result.get('initial_validation') or [])} checks"},
        {"step": "Anomaly detection", "detail": _anomaly_timeline(result.get("anomaly_detection"))},
        {"step": "Initial quality score", "detail": _score_timeline(result.get("quality_score"), "initial")},
        {"step": "Auto-healing", "detail": f"{len(healing)} healers; {repaired} repaired; {partial} partial"},
        {"step": "Final profiling and validation", "detail": f"{len(result.get('final_validation') or [])} checks"},
        {"step": "Final quality score", "detail": _score_timeline(result.get("quality_score"), "final")},
    ]


def _issue(label: str, before: Any, after: Any) -> dict[str, Any]:
    return {"label": label, "before": before, "after": after, "delta": after - before}


def _validation_index(results: Any) -> dict[tuple[str, Any], tuple[str, Any]]:
    index = {}
    for item in results if isinstance(results, list) else []:
        if not isinstance(item, dict):
            continue
        name = str(item.get("validator_name", "Validation"))
        metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
        validator_key = _validator_key(name)
        column = metadata.get("column") or _column_from_message(item.get("message"))
        label = _friendly_validator_name(name, column)
        index[(validator_key, column)] = (label, item.get("rows_affected", 0) or 0)
    return index


def _column_from_message(message: Any) -> str | None:
    match = re.search(r"column ['\"]([^'\"]+)['\"]", str(message or ""), re.IGNORECASE)
    return match.group(1) if match else None


def _validator_key(name: str) -> str:
    lowered = name.lower()
    if "null" in lowered:
        return "null"
    if "duplicate" in lowered:
        return "duplicate"
    if "data type" in lowered:
        return "datatype"
    if "regex" in lowered:
        return "regex"
    return lowered


def _friendly_validator_name(name: Any, column: Any = None) -> str:
    key = _validator_key(str(name))
    labels = {
        "null": "Missing values",
        "duplicate": "Duplicate records",
        "datatype": "Datatype",
        "regex": "Invalid formatting",
    }
    label = labels.get(key, str(name))
    return f"{label}: {column}" if column else label


def _friendly_healer_name(name: Any) -> str:
    value = str(name or "Healer")
    return value.removesuffix(" Healer")


def _schema_status(schema: Any) -> str:
    if isinstance(schema, dict) and schema.get("status") is True:
        return "Valid"
    if isinstance(schema, dict) and schema.get("status") is False:
        return "Issues found"
    return "Not available"


def _anomaly_timeline(anomaly: Any) -> str:
    if not isinstance(anomaly, dict) or not anomaly.get("enabled"):
        return "Disabled"
    return f"{anomaly.get('anomaly_count', 0)} flagged"


def _score_timeline(quality: Any, phase: str) -> str:
    if not isinstance(quality, dict) or not quality.get("enabled"):
        return "Disabled"
    score = (quality.get(phase) or {}).get("score")
    return _score_value(score)


def _reduction_percent(before: Any, after: Any) -> float:
    if not isinstance(before, (int, float)) or not isinstance(after, (int, float)):
        return 0.0
    if before <= 0:
        return 0.0
    return round(max(0.0, min(100.0, ((before - after) / before) * 100)), 2)


def render_quality_score(quality_score: Any) -> None:
    st.subheader("Quality overview")
    if not isinstance(quality_score, dict) or not quality_score.get("enabled"):
        st.info("Quality scoring is disabled for this run.")
        return

    initial = quality_score.get("initial")
    final = quality_score.get("final")
    if not isinstance(initial, dict) or not isinstance(final, dict):
        st.info("Quality score values were not returned for this run.")
        return

    score_columns = st.columns(3)
    score_columns[0].metric("Before", _score_value(initial.get("score")))
    score_columns[1].metric("After", _score_value(final.get("score")))
    delta = quality_score.get("delta")
    score_columns[2].metric(
        "Score change",
        f"{_score_delta(delta)} points" if _is_number(delta) else "Not available",
    )

    initial_components = initial.get("components")
    final_components = final.get("components")
    if isinstance(initial_components, dict) and isinstance(final_components, dict):
        component_names = [
            name for name in final_components if name in initial_components
        ]
        if component_names:
            st.markdown("**Component scores**")
            component_columns = st.columns(min(len(component_names), 3))
            for index, name in enumerate(component_names):
                before = initial_components[name]
                after = final_components[name]
                component_columns[index % len(component_columns)].metric(
                    _label(name),
                    f"{_score_value(before)} → {_score_value(after)}",
                )


def render_data_metrics(metrics: Any) -> None:
    st.subheader("Data quality metrics")
    if not isinstance(metrics, dict):
        st.info("No before and after metrics were returned.")
        return

    labels = {
        "missing_values": "Missing values",
        "duplicates": "Duplicate rows",
        "rows": "Rows processed",
    }
    available = [
        (key, label, metrics[key])
        for key, label in labels.items()
        if isinstance(metrics.get(key), dict)
        and "before" in metrics[key]
        and "after" in metrics[key]
    ]
    if not available:
        st.info("No before and after metrics were returned.")
        return

    columns = st.columns(len(available))
    for index, (_key, label, values) in enumerate(available):
        before = values["before"]
        after = values["after"]
        displayed = f"{_format_value(before)} → {_format_value(after)}"
        delta = values.get("delta")
        columns[index].metric(label, displayed)
        if delta is not None:
            columns[index].caption(f"Change: {_format_delta(delta)}")


def render_schema(schema: Any) -> None:
    st.subheader("Schema")
    if not isinstance(schema, dict):
        st.info("No schema result was returned.")
        return

    status = schema.get("status")
    if status is True:
        st.success("Schema checks passed.")
    elif status is False:
        st.warning("Schema checks found issues.")
    else:
        st.info("Schema result returned without a status.")

    rows: list[tuple[str, str, str]] = []
    for column in _string_list(schema.get("missing_columns")):
        rows.append(("Missing required column", column, "Required column is missing"))

    metadata = schema.get("metadata")
    allow_extra = isinstance(metadata, dict) and metadata.get("allow_extra_columns") is True
    for column in _string_list(schema.get("unexpected_columns")):
        details = "Unexpected column (allowed)" if allow_extra else "Unexpected column"
        rows.append(("Unexpected column", column, details))

    datatype_mismatches = schema.get("datatype_mismatches")
    if isinstance(datatype_mismatches, dict):
        for column, mismatch in datatype_mismatches.items():
            if isinstance(mismatch, dict):
                expected = mismatch.get("expected", "unknown")
                actual = mismatch.get("actual", "unknown")
                details = f"Expected {expected}; received {actual}"
            else:
                details = _format_value(mismatch)
            rows.append(("Datatype mismatch", str(column), details))

    nullable_violations = schema.get("nullable_violations")
    if isinstance(nullable_violations, dict):
        for column, violation in nullable_violations.items():
            null_count = violation.get("null_count") if isinstance(violation, dict) else None
            details = (
                f"{_format_value(null_count)} null values in a non-nullable column"
                if null_count is not None
                else "Non-nullable column contains null values"
            )
            rows.append(("Nullable violation", str(column), details))

    if rows:
        _render_table(("Finding", "Column", "Details"), rows)
    elif schema.get("message"):
        st.caption(str(schema["message"]))


def render_validation(
    initial_results: Any,
    final_results: Any,
    *,
    schema_failed: bool = False,
) -> None:
    st.subheader("Validation")
    initial = initial_results if isinstance(initial_results, list) else []
    final = final_results if isinstance(final_results, list) else []
    if not initial and not final:
        if schema_failed:
            st.info("Validation did not run because required schema columns were missing.")
        else:
            st.info("No validation results were returned.")
        return

    rows: list[tuple[str, str, str, str, str]] = []
    for phase, results in (("Before healing", initial), ("After healing", final)):
        for result in results:
            if not isinstance(result, dict):
                continue
            status = result.get("status")
            status_text = "Passed" if status is True else "Failed" if status is False else "Unknown"
            rows.append(
                (
                    phase,
                    str(result.get("validator_name", "Validator")),
                    status_text,
                    _format_value(result.get("rows_affected", "—")),
                    str(result.get("message", "")),
                )
            )

    if rows:
        _render_table(("Phase", "Validator", "Status", "Rows affected", "Details"), rows)
    else:
        st.info("No readable validation results were returned.")


def render_healing(healing: Any, *, schema_failed: bool = False) -> None:
    st.subheader("Auto-healing")
    if not isinstance(healing, list) or not healing:
        if schema_failed:
            st.info("Auto-healing did not run because required schema columns were missing.")
        else:
            st.info("No automatic repairs were required.")
        return

    actions = [action for action in healing if isinstance(action, dict)]
    if not actions:
        st.info("No readable healing actions were returned.")
        return

    rows = [
        (
            str(action.get("healer_name", "Healer")),
            str(action.get("status", "Unknown")),
            _format_value(action.get("rows_affected", "—")),
            str(action.get("message", "")),
        )
        for action in actions
    ]
    _render_table(("Healer", "Status", "Rows affected", "Action details"), rows)

    for index, action in enumerate(actions, start=1):
        healer_name = str(action.get("healer_name", f"Healer {index}"))
        metadata = action.get("metadata")
        message = action.get("message")
        if message or (isinstance(metadata, dict) and metadata):
            with st.expander(f"{healer_name} details"):
                if message:
                    st.write(str(message))
                if isinstance(metadata, dict) and metadata:
                    st.json(metadata)


def render_anomalies(anomaly_result: Any, *, schema_failed: bool = False) -> None:
    st.subheader("Anomaly detection")
    if anomaly_result is None:
        if schema_failed:
            st.info("Anomaly detection did not run because required schema columns were missing.")
        else:
            st.info("Anomaly detection disabled for this run.")
        return
    if not isinstance(anomaly_result, dict):
        st.info("Anomaly detection result was not returned.")
        return
    if anomaly_result.get("enabled") is False or anomaly_result.get("status") == "disabled":
        st.info("Anomaly detection disabled for this run.")
        return
    if anomaly_result.get("enabled") is not True:
        st.info("Anomaly detection status was not supplied.")
        return

    count = anomaly_result.get("anomaly_count")
    st.metric("Anomalies detected", _format_value(count) if count is not None else "Not supplied")
    detector = anomaly_result.get("detector_name")
    if detector:
        st.caption(f"Detector: {detector}")
    indices = anomaly_result.get("anomaly_indices")
    if isinstance(indices, list) and indices:
        with st.expander("View affected row indices"):
            st.code(", ".join(str(index) for index in indices), language=None)
    elif isinstance(indices, list):
        st.caption("No anomaly row indices were reported.")
    features = anomaly_result.get("feature_columns")
    if isinstance(features, list) and features:
        st.caption("Features: " + ", ".join(str(feature) for feature in features))
    st.info("Detected anomalies are flagged for review and are not automatically healed.")


def render_audit(
    audit_trail: Any,
    *,
    result: dict[str, Any],
    run_id: Any,
    dataset_name: Any,
) -> None:
    st.subheader("Audit and run details")
    if not isinstance(audit_trail, dict):
        st.info("No audit information was returned.")
        return

    dataset = audit_trail.get("dataset")
    dataset = dataset if isinstance(dataset, dict) else {}
    processed_at = dataset.get("processed_at")
    execution_time = result.get("execution_time", audit_trail.get("execution_time"))
    validations = audit_trail.get("validation")
    validations = validations if isinstance(validations, dict) else {}
    initial = validations.get("initial", result.get("initial_validation"))
    final = validations.get("final", result.get("final_validation"))
    healing = result.get("healing")
    healing_count = len(healing) if isinstance(healing, list) else 0

    if run_id:
        st.caption("Run ID")
        st.code(str(run_id), language=None)
    if dataset_name:
        st.caption(f"Dataset: {dataset_name}")
    if processed_at:
        st.caption(f"Processed at: {processed_at}")

    first_row = st.columns(4)
    first_row[0].metric("Execution time", _duration(execution_time))
    first_row[1].metric("Healers executed", str(healing_count))
    first_row[2].metric("Validators before", str(len(initial)) if isinstance(initial, list) else "Not supplied")
    first_row[3].metric("Validators after", str(len(final)) if isinstance(final, list) else "Not supplied")
    quality_score = result.get("quality_score")
    quality_delta = quality_score.get("delta") if isinstance(quality_score, dict) else None
    st.metric(
        "Quality score change",
        f"{_score_delta(quality_delta)} points" if _is_number(quality_delta) else "Not available",
    )

    audit_details = {
        "dataset": {"processed_at": processed_at} if processed_at else {},
        "schema": audit_trail.get("schema"),
        "validation": audit_trail.get("validation"),
        "anomalies": audit_trail.get("anomalies"),
        "healing_actions": audit_trail.get("healing_actions"),
        "metrics": audit_trail.get("metrics"),
        "quality_score": audit_trail.get("quality_score"),
        "execution_time": audit_trail.get("execution_time"),
    }
    with st.expander("View structured audit details"):
        st.json(audit_details)


def _render_table(headers: tuple[str, ...], rows: list[tuple[str, ...]]) -> None:
    header_html = "".join(f"<th scope=\"col\">{escape(header)}</th>" for header in headers)
    row_html = "".join(
        "<tr>" + "".join(f"<td>{escape(value)}</td>" for value in row) + "</tr>"
        for row in rows
    )
    st.markdown(
        '<div class="result-table-wrap"><table class="result-table">'
        f"<thead><tr>{header_html}</tr></thead><tbody>{row_html}</tbody>"
        "</table></div>",
        unsafe_allow_html=True,
    )


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _score_value(value: Any) -> str:
    return f"{value:.2f}" if _is_number(value) else "Not available"


def _score_delta(value: Any) -> str:
    return f"{value:+.2f}" if _is_number(value) else "Not available"


def _duration(value: Any) -> str:
    return f"{value:.3f} s" if _is_number(value) else "Not available"


def _format_value(value: Any) -> str:
    if _is_number(value):
        return f"{value:,}"
    if value is None:
        return "—"
    return str(value)


def _format_delta(value: Any) -> str:
    if _is_number(value):
        return f"{value:+,}"
    return str(value)


def _label(value: str) -> str:
    return value.replace("_", " ").title()
