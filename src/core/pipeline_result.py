"""Result container for complete pipeline execution."""

from __future__ import annotations

from numbers import Integral, Real
from typing import Any

import pandas as pd

from profiling.profile_result import ProfileResult


class PipelineResult:
    def __init__(
        self,
        dataframe: pd.DataFrame,
        initial_schema_result: object | None = None,
        initial_profile: ProfileResult | None = None,
        initial_validation: list[object] | None = None,
        healed_dataframe: pd.DataFrame | None = None,
        healing_results: list[object] | None = None,
        final_profile: ProfileResult | None = None,
        final_validation: list[object] | None = None,
        anomaly_detection_result: object | None = None,
        initial_quality_score: object | None = None,
        final_quality_score: object | None = None,
        quality_score: dict | None = None,
        audit_trail: dict | None = None,
        metrics: dict | None = None,
        profile_result: ProfileResult | None = None,
        validation_results: list[object] | None = None,
    ) -> None:
        self.dataframe = dataframe
        self.initial_schema_result = initial_schema_result
        self.initial_profile = (
            initial_profile if initial_profile is not None else profile_result
        )
        self.initial_validation = (
            initial_validation
            if initial_validation is not None
            else validation_results or []
        )
        self.healed_dataframe = (
            healed_dataframe if healed_dataframe is not None else dataframe
        )
        self.healing_results = healing_results or []
        self.final_profile = (
            final_profile if final_profile is not None else self.initial_profile
        )
        self.final_validation = (
            final_validation if final_validation is not None else self.initial_validation
        )
        self.anomaly_detection_result = anomaly_detection_result
        self.initial_quality_score = initial_quality_score
        self.final_quality_score = final_quality_score
        self.quality_score = quality_score or {}
        self.audit_trail = audit_trail or {}
        self.metrics = metrics or {}
        self.execution_time = 0.0

        # Backwards-compatible aliases for existing callers.
        self.profile_result = self.initial_profile
        self.validation_results = self.initial_validation
        self.schema_result = self.initial_schema_result

    def to_dict(self) -> dict[str, Any]:
        """Return an API-safe representation without embedding DataFrames."""

        return {
            "schema": self._serialize(self.initial_schema_result),
            "initial_profile": self._serialize(self.initial_profile),
            "initial_validation": self._serialize(self.initial_validation),
            "anomaly_detection": self._serialize(self.anomaly_detection_result),
            "healing": self._serialize(self.healing_results),
            "final_profile": self._serialize(self.final_profile),
            "final_validation": self._serialize(self.final_validation),
            "quality_score": self._serialize(self.quality_score),
            "metrics": self._serialize(self.metrics),
            "audit_trail": self._serialize(self.audit_trail),
            "execution_time": float(self.execution_time),
        }

    @classmethod
    def _serialize(cls, value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, (str, bool, int, float)):
            return value
        if isinstance(value, Integral):
            return int(value)
        if isinstance(value, Real):
            return float(value)
        if isinstance(value, dict):
            return {str(key): cls._serialize(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [cls._serialize(item) for item in value]

        to_dict = getattr(value, "to_dict", None)
        if isinstance(to_dict, dict):
            return cls._serialize(to_dict)
        if callable(to_dict):
            return cls._serialize(to_dict())

        if isinstance(value, pd.DataFrame):
            return None
        if hasattr(value, "__dict__"):
            return {
                key: cls._serialize(item)
                for key, item in value.__dict__.items()
                if key not in {"dataframe", "healed_dataframe"}
            }
        return str(value)

    def __repr__(self) -> str:
        return (
            "PipelineResult("
            f"initial_schema_result={self.initial_schema_result}, "
            f"initial_profile={self.initial_profile}, "
            f"initial_validation={self.initial_validation}, "
            f"healing_results={self.healing_results}, "
            f"final_profile={self.final_profile}, "
            f"final_validation={self.final_validation})"
        )
