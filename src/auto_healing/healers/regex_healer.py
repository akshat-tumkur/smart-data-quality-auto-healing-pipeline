"""Regex-style light normalization healing plugin."""

from __future__ import annotations

from time import perf_counter
from typing import Any, Sequence

import pandas as pd

from auto_healing.base_healer import BaseHealer
from auto_healing.healing_result import HealingResult


class RegexHealer(BaseHealer):
    """Apply deterministic text normalization to string-like columns."""

    display_name = "Regex Healer"

    def __init__(self, columns: Sequence[str] | None = None) -> None:
        """Initialize the healer with an optional subset of columns."""

        self.columns = list(columns) if columns is not None else None

    def heal(self, dataframe: pd.DataFrame) -> tuple[pd.DataFrame, HealingResult]:
        """Normalize strings and return the updated DataFrame and result."""

        start_time = perf_counter()

        try:
            working_dataframe = dataframe
            target_columns = self.columns or list(working_dataframe.columns)
            total_changes = 0
            transformed_columns: dict[str, dict[str, Any]] = {}
            skipped_columns: dict[str, str] = {}

            for column in target_columns:
                if column not in working_dataframe.columns:
                    skipped_columns[column] = "Column not found."
                    continue

                series = working_dataframe[column]
                if not (
                    pd.api.types.is_string_dtype(series)
                    or pd.api.types.is_object_dtype(series)
                    or pd.api.types.is_categorical_dtype(series)
                ):
                    skipped_columns[column] = "Column is not string-like."
                    continue

                normalized_series = series.astype("string")
                transformed_series = normalized_series.str.strip()

                lowered_name = column.lower()
                operations: list[str] = ["strip_whitespace"]
                if "email" in lowered_name:
                    transformed_series = transformed_series.str.lower()
                    operations.append("lowercase_email")
                if any(token in lowered_name for token in ("phone", "mobile", "tel")):
                    transformed_series = transformed_series.str.replace(
                        r"[\s-]+",
                        "",
                        regex=True,
                    )
                    operations.append("normalize_phone")

                changed_mask = normalized_series.notna() & (
                    transformed_series.astype(object) != normalized_series.astype(object)
                )
                changed_count = int(changed_mask.sum())
                if changed_count == 0:
                    continue

                working_dataframe[column] = transformed_series
                total_changes += changed_count
                transformed_columns[column] = {
                    "operations": operations,
                    "changed_count": changed_count,
                }

            message = (
                f"Normalized {total_changes} text values."
                if total_changes > 0
                else "No text normalization was applied."
            )
            metadata = {
                "transformed_columns": transformed_columns,
                "skipped_columns": skipped_columns,
            }
            return (
                working_dataframe,
                self.build_result(
                    status="success",
                    message=message,
                    rows_affected=total_changes,
                    execution_time=perf_counter() - start_time,
                    metadata=metadata,
                ),
            )
        except Exception as exc:
            return (
                dataframe,
                self.build_result(
                    status="failed",
                    message="Regex healing failed.",
                    rows_affected=0,
                    execution_time=perf_counter() - start_time,
                    metadata={
                        "exception_type": type(exc).__name__,
                        "exception_message": str(exc),
                    },
                ),
            )