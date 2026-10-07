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
            "healing_actions": self._healing_records(
                healing_results,
                initial_validation,
                final_validation,
            ),
            "metrics": metrics,
            "quality_score": quality_score,
            "execution_time": execution_time,
        }

    def _healing_records(
        self,
        healing_results: Iterable[Any],
        initial_validation: Iterable[Any],
        final_validation: Iterable[Any],
    ) -> list[dict[str, Any]]:
        initial_validation = list(initial_validation)
        final_validation = list(final_validation)
        return [
            self._healing_record(result, initial_validation, final_validation)
            for result in healing_results
        ]

    def _healing_record(
        self,
        result: Any,
        initial_validation: list[Any],
        final_validation: list[Any],
    ) -> dict[str, Any]:
        metadata = getattr(result, "metadata", {}) or {}
        summary = metadata.get("summary", {})
        operation = summary.get("operation", getattr(result, "healer_name", ""))
        validation_type = self._operation_validation_type(operation)
        initial_affected = self._validation_count(initial_validation, validation_type)
        remaining = self._validation_count(final_validation, validation_type)
        record = {
            "operation": operation,
            "status": getattr(result, "status", "failed"),
            "success": getattr(result, "status", "failed") == "success" and remaining == 0,
            "rows_affected": int(getattr(result, "rows_affected", 0)),
            "execution_time": getattr(result, "execution_time", 0.0),
            "initial_affected": initial_affected,
            "remaining": remaining,
            "repaired": max(initial_affected - remaining, 0),
            "details": metadata,
        }
        for key in (
            "attempted",
            "changed",
            "failed",
            "unresolved",
            "cells_changed",
            "columns_affected",
        ):
            if key in metadata:
                record[key] = metadata[key]
            elif key in summary:
                record[key] = summary[key]
        return record

    @staticmethod
    def _operation_validation_type(operation: str) -> str:
        name = operation.lower()
        if "missing" in name:
            return "missing"
        if "duplicate" in name:
            return "duplicate"
        if "datatype" in name:
            return "datatype"
        if "regex" in name:
            return "regex"
        return ""

    @staticmethod
    def _validation_count(results: list[Any], validation_type: str) -> int:
        if not validation_type:
            return 0
        counts = []
        for result in results:
            name = str(getattr(result, "validator_name", "")).lower()
            if (
                (validation_type == "missing" and "null" in name)
                or (validation_type == "duplicate" and "duplicate" in name)
                or (validation_type == "datatype" and "data type" in name)
                or (validation_type == "regex" and "regex" in name)
            ):
                counts.append(int(getattr(result, "rows_affected", 0)))
        return sum(counts)

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