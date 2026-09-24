import pandas as pd

from anomaly_detection import AnomalyDetectorFactory, IsolationForestDetector


def test_isolation_forest_detects_anomalies_without_modifying_dataframe():
    dataframe = pd.DataFrame(
        {
            "employee_id": ["EMP1", "EMP2", "EMP3", "EMP4", "EMP5", "EMP6"],
            "salary": [10, 11, 10, 12, 11, 1000],
            "age": [30, 31, 29, 32, 30, 80],
        }
    )
    original = dataframe.copy(deep=True)

    result = IsolationForestDetector(contamination=0.2, random_state=42).detect(dataframe)

    assert result.enabled is True
    assert result.detector_name == "Isolation Forest"
    assert result.anomaly_count >= 1
    assert "salary" in result.feature_columns
    assert "age" in result.feature_columns
    assert "employee_id" not in result.feature_columns
    assert dataframe.equals(original)
    assert isinstance(result.to_dict["anomaly_indices"], list)


def test_isolation_forest_handles_missing_values_and_no_numeric_features():
    dataframe = pd.DataFrame(
        {
            "name": ["a", "b"],
            "value": [None, None],
        }
    )

    result = IsolationForestDetector(random_state=42).detect(dataframe)

    assert result.anomaly_indices == []
    assert result.metadata["reason"] == "Insufficient suitable numeric data."


def test_isolation_forest_is_deterministic_for_same_input_and_seed():
    dataframe = pd.DataFrame({"value": [1, 2, 3, 4, 100]})
    detector = IsolationForestDetector(contamination=0.2, random_state=42)

    first = detector.detect(dataframe)
    second = detector.detect(dataframe)

    assert first.anomaly_indices == second.anomaly_indices


def test_anomaly_detection_factory_is_disabled_by_default():
    assert AnomalyDetectorFactory().build() is None