"""Anomaly detection plugin contracts and result model."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import pandas as pd


class AnomalyResult:
	"""Serializable output from one anomaly detector run."""

	def __init__(
		self,
		enabled: bool,
		detector_name: str = "",
		anomaly_indices: list[Any] | None = None,
		feature_columns: list[str] | None = None,
		execution_time: float = 0.0,
		metadata: dict[str, Any] | None = None,
	) -> None:
		self.enabled = enabled
		self.detector_name = detector_name
		self.anomaly_indices = anomaly_indices or []
		self.anomaly_count = len(self.anomaly_indices)
		self.feature_columns = feature_columns or []
		self.execution_time = execution_time
		self.metadata = metadata or {}

	@property
	def status(self) -> str:
		return "disabled" if not self.enabled else "completed"

	@property
	def to_dict(self) -> dict[str, Any]:
		return {
			"enabled": self.enabled,
			"status": self.status,
			"detector_name": self.detector_name,
			"anomaly_indices": list(self.anomaly_indices),
			"anomaly_count": self.anomaly_count,
			"feature_columns": list(self.feature_columns),
			"execution_time": self.execution_time,
			"metadata": dict(self.metadata),
		}


class AnomalyDetector(ABC):
	"""Base contract for pluggable anomaly detectors."""

	@abstractmethod
	def detect(self, dataframe: pd.DataFrame) -> AnomalyResult:
		"""Detect anomalies without modifying the supplied DataFrame."""


class AnomalyDetectorFactory:
	"""Build the configured anomaly detector plugin."""

	def build(self, config: dict[str, Any] | None = None) -> AnomalyDetector | None:
		config = config or {}
		if not config.get("enabled", False):
			return None

		from anomaly_detection.isolation_forest import IsolationForestDetector

		method = config.get("method", "isolation_forest")
		if method != "isolation_forest":
			raise ValueError(f"Unsupported anomaly detection method: {method}")
		return IsolationForestDetector(
			contamination=float(config.get("contamination", 0.05)),
			random_state=int(config.get("random_state", 42)),
		)
