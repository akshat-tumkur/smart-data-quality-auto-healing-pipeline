"""Configurable, deterministic data quality scoring."""

from __future__ import annotations

from typing import Any, Iterable


class QualityScore:
    """Serializable quality score and component metrics."""

    def __init__(
        self,
        enabled: bool,
        score: float | None,
        components: dict[str, float],
        weights: dict[str, float],
        metrics: dict[str, Any],
    ) -> None:
        self.enabled = enabled
        self.score = score
        self.components = components
        self.weights = weights
        self.metrics = metrics

    @property
    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "score": self.score,
            "components": dict(self.components),
            "weights": dict(self.weights),
            "metrics": dict(self.metrics),
        }


class QualityScoreCalculator:
    """Calculate weighted completeness, validity, and uniqueness scores.

    Each component is normalized to 0-100. Completeness is the percentage of
    non-null cells, validity is the percentage of rows not affected by failed
    validators, and uniqueness is the percentage of rows not marked duplicate.
    The overall score is the weighted average of the configured components.
    """

    DEFAULT_WEIGHTS = {
        "completeness": 0.4,
        "validity": 0.3,
        "uniqueness": 0.3,
    }

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        config = config or {}
        self.enabled = bool(config.get("enabled", False))
        configured_weights = config.get("weights", {})
        self.weights = self._normalize_weights(configured_weights)

    def calculate(self, profile: Any, validation_results: Iterable[Any]) -> QualityScore:
        if not self.enabled:
            return QualityScore(False, None, {}, self.weights, {})

        validation_results = list(validation_results)
        row_count = max(int(getattr(profile, "row_count", 0)), 0)
        column_count = max(int(getattr(profile, "column_count", 0)), 0)
        total_cells = row_count * column_count
        missing_values = int(getattr(profile, "total_missing_values", 0))
        duplicate_rows = self._duplicate_rows(profile, validation_results)
        affected_rows = self._validation_affected_rows(validation_results, row_count)

        completeness = self._percentage(
            total_cells - missing_values,
            total_cells,
        )
        validity = self._percentage(row_count - affected_rows, row_count)
        uniqueness = self._percentage(row_count - duplicate_rows, row_count)
        components = {
            "completeness": completeness,
            "validity": validity,
            "uniqueness": uniqueness,
        }
        score = sum(components[name] * self.weights[name] for name in components)

        return QualityScore(
            enabled=True,
            score=round(score, 4),
            components=components,
            weights=self.weights,
            metrics={
                "row_count": row_count,
                "column_count": column_count,
                "missing_values": missing_values,
                "duplicate_rows": duplicate_rows,
                "validation_affected_rows": affected_rows,
            },
        )

    @staticmethod
    def _validation_affected_rows(validation_results: list[Any], row_count: int) -> int:
        invalid_indices: set[Any] = set()
        fallback_count = 0
        for result in validation_results:
            if bool(getattr(result, "status", False)):
                continue
            metadata = getattr(result, "metadata", {}) or {}
            indices = metadata.get("invalid_indices", metadata.get("duplicate_indices"))
            if indices is None:
                fallback_count = max(
                    fallback_count,
                    int(getattr(result, "rows_affected", 0)),
                )
            else:
                invalid_indices.update(indices)

        return min(max(len(invalid_indices), fallback_count), row_count)

    @staticmethod
    def _duplicate_rows(profile: Any, validation_results: list[Any]) -> int:
        """Use configured duplicate-validator metadata when available.

        The profiler measures full-row duplicates, while duplicate validation
        may use a configured subset such as ``email``. The validation result
        is therefore the authoritative uniqueness metric for this score.
        """

        duplicate_results = [
            result
            for result in validation_results
            if str(getattr(result, "validator_name", "")).lower().startswith("duplicate")
        ]
        if duplicate_results:
            indices: set[Any] = set()
            for result in duplicate_results:
                metadata = getattr(result, "metadata", {}) or {}
                indices.update(metadata.get("duplicate_indices", []))
            return len(indices)

        return int(getattr(profile, "duplicate_rows", 0))

    def compare(self, initial: QualityScore, final: QualityScore) -> dict[str, Any]:
        if not initial.enabled or not final.enabled:
            return {"enabled": False, "initial": None, "final": None, "delta": None}

        return {
            "enabled": True,
            "initial": initial.to_dict,
            "final": final.to_dict,
            "delta": round((final.score or 0) - (initial.score or 0), 4),
        }

    def _normalize_weights(self, configured: Any) -> dict[str, float]:
        weights = dict(self.DEFAULT_WEIGHTS)
        if isinstance(configured, dict):
            for name in weights:
                if name in configured:
                    weights[name] = max(float(configured[name]), 0.0)

        total = sum(weights.values())
        if total <= 0:
            return dict(self.DEFAULT_WEIGHTS)
        return {name: value / total for name, value in weights.items()}

    @staticmethod
    def _percentage(numerator: int, denominator: int) -> float:
        if denominator <= 0:
            return 100.0
        return round(max(0.0, min(100.0, numerator / denominator * 100)), 4)