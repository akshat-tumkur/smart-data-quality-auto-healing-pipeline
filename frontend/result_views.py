"""Render API-backed quality, metric, schema, and validation sections."""

from __future__ import annotations

from html import escape
from typing import Any

import streamlit as st


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
