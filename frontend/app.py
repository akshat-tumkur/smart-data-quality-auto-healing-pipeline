"""Streamlit dashboard shell for the Adaptive Data Quality Platform."""

import streamlit as st

try:
    from frontend.services.api_client import (
        PipelineApiClient,
        PipelineApiError,
        friendly_error_message,
    )
    from frontend.result_views import (
        render_anomalies,
        render_audit,
        render_data_metrics,
        render_healing,
        render_quality_score,
        render_schema,
        render_validation,
    )
except ModuleNotFoundError:
    from services.api_client import (
        PipelineApiClient,
        PipelineApiError,
        friendly_error_message,
    )
    from result_views import (
        render_anomalies,
        render_audit,
        render_data_metrics,
        render_healing,
        render_quality_score,
        render_schema,
        render_validation,
    )


api_client = PipelineApiClient()
try:
    health_payload = api_client.get_health()
    api_connected = health_payload.get("status") == "ok"
except Exception:
    api_connected = False

for state_key, initial_value in (
    ("pipeline_result", None),
    ("pipeline_error", None),
    ("run_id", None),
    ("dataset_name", None),
    ("upload_identity", None),
):
    if state_key not in st.session_state:
        st.session_state[state_key] = initial_value

st.set_page_config(
    page_title="Adaptive Data Quality Platform",
    page_icon="▦",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
      :root { --ink: #17212b; --muted: #667482; --line: #dce3e8; --accent: #176b87; }
      .block-container { max-width: 1440px; padding-top: 2rem; padding-bottom: 3rem; }
      [data-testid="stSidebar"] { border-right: 1px solid var(--line); }
      [data-testid="stSidebar"] > div:first-child { padding-top: 1.5rem; }
      .brand-mark {
        display: inline-flex; align-items: center; justify-content: center;
        width: 2.15rem; height: 2.15rem; margin-right: .55rem;
        border-radius: .45rem; background: #e7f2f5; color: var(--accent);
        font-size: 1.2rem; font-weight: 700; vertical-align: middle;
      }
      .eyebrow { color: var(--muted); font-size: .76rem; font-weight: 650;
        letter-spacing: .09em; text-transform: uppercase; }
    .status-pill {
        display: inline-block; border: 1px solid var(--line); border-radius: 999px;
        padding: .28rem .65rem; color: #465563; background: #f7f9fa;
        font-size: .78rem; font-weight: 600;
      }
      .status-online { color: #17603c; border-color: #b8dec8; background: #eff8f2; }
      .status-offline { color: #8c3d31; border-color: #edc8c2; background: #fff5f3; }
      .surface-muted { color: var(--muted); }
      .stage-row { padding: .6rem 0; border-bottom: 1px solid #edf0f2; }
      .stage-row:last-child { border-bottom: 0; }
      .stage-index { color: var(--accent); font-weight: 700; margin-right: .65rem; }
      div[data-testid="stFileUploader"] { border-radius: .5rem; }
      .result-table-wrap { overflow-x: auto; width: 100%; }
      .result-table { border-collapse: collapse; width: 100%; font-size: .9rem; }
      .result-table th { background: #f4f7f8; color: #34424e; font-weight: 650; text-align: left; }
      .result-table th, .result-table td { border-bottom: 1px solid #e4e9ec; padding: .65rem .75rem; vertical-align: top; }
      .result-table td { color: #34424e; }
      @media (max-width: 900px) {
        .block-container { padding: 1.25rem 1rem 2rem; }
        .result-table { min-width: 620px; }
      }
    </style>
    """,
    unsafe_allow_html=True,
)


with st.sidebar:
    st.markdown(
        '<span class="brand-mark">▦</span><strong>Adaptive Data Quality</strong>',
        unsafe_allow_html=True,
    )
    st.caption("Engineering workspace")
    st.divider()
    st.markdown("**Workspace**")
    st.markdown("▰  Overview")
    st.divider()
    st.markdown("**Current run**")
    if st.session_state.run_id:
        st.code(st.session_state.run_id, language=None)
        st.caption(st.session_state.dataset_name or "Dataset")
    else:
        st.caption("No run yet")
        st.caption("Upload a CSV to start an analysis.")


header_left, header_right = st.columns([5, 1], vertical_alignment="center")
with header_left:
    st.markdown('<div class="eyebrow">Data quality / Overview</div>', unsafe_allow_html=True)
    st.title("Adaptive Data Quality Platform")
    st.caption("Profile, validate, and automatically repair datasets through one pipeline.")
with header_right:
    if api_connected:
        st.markdown('<span class="status-pill status-online">● API connected</span>', unsafe_allow_html=True)
    else:
        st.markdown('<span class="status-pill status-offline">● API unavailable</span>', unsafe_allow_html=True)

st.divider()

upload_column, pipeline_column = st.columns([1.65, 1], gap="large")

with upload_column:
    st.subheader("New analysis")
    with st.container(border=True):
        st.markdown("**Upload dataset**")
        st.caption("CSV files are supported. Your data is processed by the existing pipeline.")
        selected_file = st.file_uploader(
            "Choose a CSV file",
            type=["csv"],
            accept_multiple_files=False,
            help="Select a CSV dataset for analysis.",
            key="dataset_upload",
        )
        upload_identity = (
            (selected_file.name, selected_file.size)
            if selected_file is not None
            else None
        )
        if upload_identity != st.session_state.upload_identity:
            st.session_state.upload_identity = upload_identity
            st.session_state.pipeline_result = None
            st.session_state.pipeline_error = None
            st.session_state.run_id = None
            st.session_state.dataset_name = None
        if selected_file is not None:
            st.caption(f"Selected: {selected_file.name} · {selected_file.size:,} bytes")
        run_clicked = st.button(
            "Run pipeline",
            type="primary",
            disabled=selected_file is None or not api_connected,
            use_container_width=True,
            help="Select a CSV and make sure the API is connected to run the pipeline.",
        )
        if not api_connected:
            st.caption("Start the FastAPI service, then interact with the page to check the connection again.")

        if run_clicked and selected_file is not None:
            st.session_state.pipeline_result = None
            st.session_state.pipeline_error = None
            st.session_state.run_id = None
            st.session_state.dataset_name = None
            try:
                with st.spinner("Running data quality pipeline..."):
                    result = api_client.run_pipeline(
                        selected_file.name,
                        selected_file.getvalue(),
                    )
                st.session_state.pipeline_result = result
                st.session_state.run_id = result.get("run_id")
                st.session_state.dataset_name = selected_file.name
            except PipelineApiError as exc:
                st.session_state.pipeline_error = friendly_error_message(exc)
                if exc.status_code == 422:
                    st.session_state.pipeline_result = exc.schema_failure_result
                    if exc.schema_failure_result:
                        st.session_state.run_id = exc.schema_failure_result.get("run_id")
                        st.session_state.dataset_name = selected_file.name
            except Exception:
                st.session_state.pipeline_error = (
                    "Could not reach the API or read its response. Check the API service and try again."
                )

with pipeline_column:
    st.subheader("Pipeline at a glance")
    with st.container(border=True):
        stages = (
            ("01", "Schema check", "Required columns and declared types"),
            ("02", "Profile and validate", "Initial dataset quality checks"),
            ("03", "Detect anomalies", "Optional; flagged for review"),
            ("04", "Auto-heal", "Configured repairs for eligible issues"),
            ("05", "Recheck and score", "Final validation and quality comparison"),
            ("06", "Audit and report", "Run details and generated outputs"),
        )
        for number, title, detail in stages:
            st.markdown(
                f'<div class="stage-row"><span class="stage-index">{number}</span>'
                f'<strong>{title}</strong><br><span class="surface-muted">{detail}</span></div>',
                unsafe_allow_html=True,
            )

st.divider()
st.subheader("Run results")
if st.session_state.pipeline_error:
    st.error(st.session_state.pipeline_error)
result = st.session_state.pipeline_result
if isinstance(result, dict):
    if result.get("status") == "success":
        st.success("Pipeline completed successfully.")
        run_id = st.session_state.run_id or result.get("run_id")
        if run_id:
            try:
                download_url = api_client.cleaned_dataset_url(run_id)
                st.link_button(
                    "Download cleaned CSV",
                    download_url,
                    type="primary",
                    help="Download the cleaned dataset produced by this run.",
                )
                st.caption("If the API reports that the cleaned file is unavailable, run the pipeline again.")
            except ValueError:
                st.error("The API returned an invalid run ID, so the cleaned file cannot be downloaded.")
    elif result.get("status") == "schema_failed":
        st.warning("The pipeline stopped because required schema columns are missing.")
    else:
        st.info("A pipeline result was returned.")
    if st.session_state.run_id:
        st.caption(f"Run ID: {st.session_state.run_id}")

    schema_failed = result.get("status") == "schema_failed"
    render_quality_score(result.get("quality_score"))
    render_data_metrics(result.get("metrics"))
    render_schema(result.get("schema"))
    render_validation(
        result.get("initial_validation"),
        result.get("final_validation"),
        schema_failed=schema_failed,
    )
    render_healing(result.get("healing"), schema_failed=schema_failed)
    render_anomalies(result.get("anomaly_detection"), schema_failed=schema_failed)
    render_audit(
        result.get("audit_trail"),
        result=result,
        run_id=st.session_state.run_id or result.get("run_id"),
        dataset_name=st.session_state.dataset_name,
    )
elif not st.session_state.pipeline_error:
    st.info("Upload a dataset to begin a quality analysis. Results will appear here after a run.", icon="ℹ️")
