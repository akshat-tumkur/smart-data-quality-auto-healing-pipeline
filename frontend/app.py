import streamlit as st
import pandas as pd
from datetime import datetime
# Page configuration
st.set_page_config(
    page_title="Smart Data Quality Pipeline",
    page_icon="📊",
    layout="wide"
)

# Title
st.title("Smart Data Quality Pipeline")
st.write("Data Quality Monitoring Dashboard")

# Sidebar
st.sidebar.title("Navigation")
page = st.sidebar.radio(
    "Go to",
    [
        "Dashboard",
        "Upload Data",
        "Cleaned Data",
        "Failed Records",
        "Anomalies"
    ]
)

# Pages
if page == "Dashboard":
    col1, col2 = st.columns([5, 1])
    with col1:
        st.title("Data Quality Dashboard")
    with col2:
        if st.button("Refresh"):
            st.rerun()
    st.write("Overview of your data quality pipeline")
    st.subheader("Pipeline Summary")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Records", 1000)
    col2.metric("Processed", 950)
    col3.metric("Failed", 50)
    col4.metric("Anomalies", 12)
    st.subheader("Data Quality Score")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Completeness", "92%")
    col2.metric("Accuracy", "88%")
    col3.metric("Consistency", "90%")
    col4.metric("Validity", "85%")
    st.metric("Overall Quality Score", "89%")
    st.progress(89, text="Overall Data Quality")
    st.subheader("Validation Issues")
    issue_data = {
        "Issue": [
            "Missing Values",
            "Duplicate Records",
            "Invalid Emails",
            "Invalid Dates"
        ],
        "Count": [35, 20, 12, 8]
    }
    st.bar_chart(
        issue_data,
        x="Issue",
        y="Count"
    )
    st.subheader("Processing Summary")
    processing_data = {
        "Status": [
            "Processed",
            "Failed",
            "Anomalies"
        ],
        "Count": [950, 50, 12]
    }
    st.bar_chart(
        processing_data,
        x="Status",
        y="Count"
    )
    st.subheader("Pipeline Status")
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
     st.info("Ingestion\nReady")
    with col2:
     st.info("Profiling\nReady")
    with col3:
     st.info("Validation\nReady")
    with col4:
     st.info("Cleaning\nReady")
    with col5:
     st.info("ML Analysis\nReady")
    st.caption(f"Last updated: {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}")

elif page == "Upload Data":
    st.title("Upload Data")
    st.write("Upload a CSV file to begin the data quality process.")
    uploaded_file = st.file_uploader(
        "Choose a CSV file",
        type=["csv"]
    )
    if uploaded_file is not None:
        st.success("File uploaded successfully!")
        st.progress(100, text="Upload complete")
        if st.button("Run Data Quality Check", type="primary"):
         st.info("Data quality check started.")
        df = pd.read_csv(uploaded_file)
        st.subheader("Dataset Information")
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Records", df.shape[0])
        col2.metric("Total Columns", df.shape[1])
        col3.metric("Missing Values", int(df.isnull().sum().sum()))
        st.subheader("Data Preview")
        st.dataframe(df)
        st.download_button(
            "Download Data",
            df.to_csv(index=False),
            "uploaded_data.csv",
            "text/csv"
        )

elif page == "Cleaned Data":
    st.title("Cleaned Data")
    st.write("Data after validation, cleaning, and auto-healing.")
    st.info("Cleaned data will appear here after pipeline processing.")

elif page == "Failed Records":
    st.title("Failed Records")
    st.write("Records that could not be processed successfully.")
    st.info("Failed records will appear here after pipeline processing.")
    st.write("Failed records will be displayed here.")

elif page == "Anomalies":
    st.title("Anomalies")
    st.write("Records identified as unusual by the ML model.")
    st.info("Anomaly results will appear here after ML processing.")