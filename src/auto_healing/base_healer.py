"""Base abstractions for auto-healing plugins."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import pandas as pd

from auto_healing.healing_result import HealingResult


class BaseHealer(ABC):
    """Abstract base class for DataFrame healers."""

    display_name: str | None = None
    validation_types: frozenset[str] = frozenset()

    @property
    def healer_name(self) -> str:
        """Return the human-readable healer name."""

        return self.display_name or self.__class__.__name__

    @staticmethod
    def _normalize_numeric_value(value: Any) -> Any:
        """Convert currency and formatting markers into a numeric-friendly string."""

        if pd.isna(value):
            return pd.NA

        if isinstance(value, str):
            cleaned = value.strip()
            if not cleaned:
                return pd.NA

            cleaned = cleaned.replace(",", "")
            cleaned = cleaned.replace("$", "")
            cleaned = cleaned.replace("€", "")
            cleaned = cleaned.replace("£", "")
            if cleaned.startswith("(") and cleaned.endswith(")"):
                cleaned = f"-{cleaned[1:-1]}"
            if cleaned.endswith("%"):
                cleaned = cleaned[:-1]
            return cleaned

        return value

    @staticmethod
    def _coerce_numeric_series(series: pd.Series) -> pd.Series:
        """Normalize numeric-like strings and convert them to pandas numeric dtype."""

        normalized_values = series.map(BaseHealer._normalize_numeric_value)
        return pd.to_numeric(normalized_values, errors="coerce")

    @staticmethod
    def _change_summary(
        before: pd.DataFrame,
        after: pd.DataFrame,
        columns: list[str] | None = None,
    ) -> dict[str, int]:
        """Return unique row/cell metrics for a set of columns."""

        chosen_columns = list(columns or list(before.columns))
        changed_rows: set[Any] = set()
        cells_changed = 0
        columns_affected = 0

        for column in chosen_columns:
            if column not in before.columns or column not in after.columns:
                continue
            before_values = before[column].map(
                lambda value: "__NA__" if pd.isna(value) else value
            )
            after_values = after[column].map(
                lambda value: "__NA__" if pd.isna(value) else value
            )
            changed_mask = before_values.combine(
                after_values,
                lambda before_value, after_value: not BaseHealer._values_equal(
                    before_value,
                    after_value,
                ),
            )
            changed_indices = before.index[changed_mask].tolist()
            if not changed_indices:
                continue
            columns_affected += 1
            cells_changed += len(changed_indices)
            changed_rows.update(changed_indices)

        return {
            "rows_affected": len(changed_rows),
            "cells_changed": cells_changed,
            "columns_affected": columns_affected,
        }

    @staticmethod
    def _values_equal(before_value: Any, after_value: Any) -> bool:
        """Compare values without treating numeric dtype-only casts as repairs."""

        before_missing = pd.isna(before_value)
        after_missing = pd.isna(after_value)
        if before_missing or after_missing:
            return bool(before_missing and after_missing)

        if isinstance(before_value, str) and isinstance(after_value, (int, float)):
            return False
        if isinstance(before_value, (int, float)) and isinstance(after_value, (int, float)):
            return bool(before_value == after_value)
        return bool(before_value == after_value)

    @staticmethod
    def summarize_status(
        *,
        attempted: int,
        changed: int,
        unresolved: int,
        default_message: str,
    ) -> tuple[str, str]:
        """Determine the best outcome status without overstating repair success."""

        if attempted == 0:
            return "success", default_message
        if changed == 0 and unresolved == 0:
            return "success", default_message
        if unresolved == 0:
            return "success", f"{default_message} ({changed} repaired)"
        if changed > 0:
            return "partial", f"{default_message} ({changed} repaired, {unresolved} unresolved)"
        return "failed", f"{default_message} ({unresolved} unresolved)"

    @abstractmethod
    def heal(self, dataframe: pd.DataFrame) -> tuple[pd.DataFrame, HealingResult]:
        """Heal the supplied DataFrame and return the updated frame and result."""

    def build_result(
        self,
        *,
        status: str,
        message: str,
        rows_affected: int,
        execution_time: float,
        metadata: dict[str, Any] | None = None,
    ) -> HealingResult:
        """Create a standardized healing result."""

        result_metadata = dict(metadata or {})
        result_metadata.setdefault(
            "summary",
            {
                "operation": self.healer_name,
                "status": status,
                "rows_affected": rows_affected,
            },
        )
        result_metadata.setdefault("metrics", {"rows_affected": rows_affected})

        return HealingResult(
            healer_name=self.healer_name,
            status=status,
            message=message,
            rows_affected=rows_affected,
            execution_time=execution_time,
            metadata=result_metadata,
        )