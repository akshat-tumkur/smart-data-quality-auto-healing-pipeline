"""Isolation Forest anomaly detector."""

from __future__ import annotations

from time import perf_counter
from typing import Any

import pandas as pd
from sklearn.ensemble import IsolationForest

from anomaly_detection.anomaly_detector import AnomalyDetector, AnomalyResult


class IsolationForestDetector(AnomalyDetector):
    """Detect unusual rows in suitable numeric, non-identifier features."""

    def __init__(
        self,
        contamination: float = 0.05,
        random_state: int = 42,
    ) -> None:
        if not 0 < contamination <= 0.5:
            raise ValueError("contamination must be greater than 0 and at most 0.5.")
        self.contamination = contamination
        self.random_state = random_state

    def detect(self, dataframe: pd.DataFrame) -> AnomalyResult:
        start_time = perf_counter()
        feature_columns = self._feature_columns(dataframe)
        if len(dataframe) < 2 or not feature_columns:
            return self._result(
                anomaly_indices=[],
                feature_columns=feature_columns,
                execution_time=perf_counter() - start_time,
                metadata={"reason": "Insufficient suitable numeric data."},
            )

        features = dataframe[feature_columns].apply(pd.to_numeric, errors="coerce")
        features = features.fillna(features.median()).fillna(0.0)
        model = IsolationForest(
            contamination=self.contamination,
            random_state=self.random_state,
        )
        predictions = model.fit_predict(features)
        anomaly_indices = dataframe.index[predictions == -1].tolist()

        return self._result(
            anomaly_indices=anomaly_indices,
            feature_columns=feature_columns,
            execution_time=perf_counter() - start_time,
            metadata={
                "method": "isolation_forest",
                "contamination": self.contamination,
                "random_state": self.random_state,
                "rows_scanned": int(len(dataframe)),
            },
        )

    def _result(
        self,
        *,
        anomaly_indices: list[Any],
        feature_columns: list[str],
        execution_time: float,
        metadata: dict[str, Any],
    ) -> AnomalyResult:
        return AnomalyResult(
            enabled=True,
            detector_name="Isolation Forest",
            anomaly_indices=anomaly_indices,
            feature_columns=feature_columns,
            execution_time=execution_time,
            metadata=metadata,
        )

    @staticmethod
    def _feature_columns(dataframe: pd.DataFrame) -> list[str]:
        numeric_columns = dataframe.select_dtypes(include="number").columns
        return [
            column
            for column in numeric_columns
            if "id" not in column.lower()
        ]
