"""Serializable audit trail construction for one pipeline run."""

from __future__ import annotations

from datetime import datetime, timezone
from numbers import Integral, Real
from typing import Any, Iterable


class AuditTrailBuilder:
    """Build metadata-only audit records without retaining dataframes."""

    def build(
        self,
        *,
        config: dict[str, Any],
        schema_result: Any,
        initial_validation: Iterable[Any],
        anomaly_result: Any,
        healing_results: Iterable[Any],
        final_validation: Iterable[Any],
        metrics: dict[str, Any],
        quality_score: dict[str, Any],
        execution_time: float,
    ) -> dict[str, Any]:
        return {
            "dataset": {
                "path": config.get("dataset", {}).get("path"),
                "processed_at": datetime.now(timezone.utc).isoformat(),
            },
            "schema": self._serialize(schema_result),
            "validation": {
                "initial": [self._serialize(item) for item in initial_validation],
                "final": [self._serialize(item) for item in final_validation],
            },
            "anomalies": self._serialize(anomaly_result),
            "healing_actions": [
                self._healing_record(item) for item in healing_results
            ],
            "metrics": metrics,
            "quality_score": quality_score,
            "execution_time": execution_time,
        }

    def _healing_record(self, result: Any) -> dict[str, Any]:
        metadata = getattr(result, "metadata", {}) or {}
        summary = metadata.get("summary", {})
        return {
            "operation": summary.get("operation", getattr(result, "healer_name", "")),
            "status": getattr(result, "status", "failed"),
            "success": getattr(result, "status", "failed") == "success",
            "rows_affected": int(getattr(result, "rows_affected", 0)),
            "execution_time": getattr(result, "execution_time", 0.0),
            "details": metadata,
        }

    def _serialize(self, value: Any) -> Any:
        if value is None:
            return None
        to_dict = getattr(value, "to_dict", None)
        if isinstance(to_dict, dict):
            return to_dict
        if hasattr(value, "__dict__"):
            return {
                key: self._serialize(item)
                for key, item in value.__dict__.items()
                if key not in {"dataframe", "healed_dataframe"}
            }
        if isinstance(value, dict):
            return {str(key): self._serialize(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [self._serialize(item) for item in value]
        if isinstance(value, Integral):
            return int(value)
        if isinstance(value, Real):
            return float(value)
        return value