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
    validation_types = frozenset({"regex"})

    def __init__(
        self,
        columns: Sequence[str] | None = None,
        lowercase_email: bool = True,
        trim_whitespace: bool = True,
        remove_phone_symbols: bool = True,
    ) -> None:
        """Initialize the healer with an optional subset of columns."""

        self.columns = list(columns) if columns is not None else None
        self.lowercase_email = lowercase_email
        self.trim_whitespace = trim_whitespace
        self.remove_phone_symbols = remove_phone_symbols

    def heal(self, dataframe: pd.DataFrame) -> tuple[pd.DataFrame, HealingResult]:
        """Normalize strings and return the updated DataFrame and result."""

        start_time = perf_counter()

        try:
            working_dataframe = dataframe.copy(deep=True)
            before_dataframe = dataframe.copy(deep=True)
            target_columns = self.columns or list(working_dataframe.columns)
            attempted = 0
            changed = 0
            unresolved = 0
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
                transformed_series = normalized_series.copy()
                lowered_name = column.lower()
                operations: list[str] = []

                if self.trim_whitespace:
                    transformed_series = transformed_series.str.strip()
                    operations.append("trim_whitespace")
                if self.lowercase_email and "email" in lowered_name:
                    transformed_series = transformed_series.str.lower()
                    operations.append("lowercase_email")
                if self.remove_phone_symbols and any(
                    token in lowered_name for token in ("phone", "mobile", "tel")
                ):
                    transformed_series = transformed_series.str.replace(
                        r"[^\d+]+",
                        "",
                        regex=True,
                    )
                    operations.append("remove_phone_symbols")

                if not operations:
                    skipped_columns[column] = "No regex healing operations enabled."
                    continue

                attempted += int(normalized_series.notna().sum())
                changed_mask = normalized_series.notna() & (
                    transformed_series.astype(object) != normalized_series.astype(object)
                )
                changed_count = int(changed_mask.sum())
                unresolved_count = self._unresolved_regex_count(
                    transformed_series,
                    column_name=column,
                )
                changed += changed_count
                unresolved += unresolved_count

                working_dataframe[column] = transformed_series
                transformed_columns[column] = {
                    "operations": operations,
                    "attempted": int(normalized_series.notna().sum()),
                    "changed_count": changed_count,
                    "unresolved_count": unresolved_count,
                }

            for column in transformed_columns:
                dataframe[column] = working_dataframe[column]

            change_summary = self._change_summary(
                before_dataframe,
                dataframe,
                columns=list(transformed_columns.keys()),
            )
            rows_affected = change_summary["rows_affected"]
            cells_changed = change_summary["cells_changed"]
            columns_affected = change_summary["columns_affected"]
            status, message = self.summarize_status(
                attempted=attempted,
                changed=changed,
                unresolved=unresolved,
                default_message=(
                    f"Normalized {changed} text values."
                    if changed > 0
                    else "No text normalization was applied."
                ),
            )
            metadata = {
                "attempted": attempted,
                "changed": changed,
                "failed": 0,
                "unresolved": unresolved,
                "unresolved_count": unresolved,
                "rows_affected": rows_affected,
                "cells_changed": cells_changed,
                "columns_affected": columns_affected,
                "transformed_columns": transformed_columns,
                "skipped_columns": skipped_columns,
                "options": {
                    "lowercase_email": self.lowercase_email,
                    "trim_whitespace": self.trim_whitespace,
                    "remove_phone_symbols": self.remove_phone_symbols,
                },
            }
            return (
                dataframe,
                self.build_result(
                    status=status,
                    message=message,
                    rows_affected=rows_affected,
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
                        "attempted": 0,
                        "changed": 0,
                        "failed": 1,
                        "unresolved": 0,
                        "exception_type": type(exc).__name__,
                        "exception_message": str(exc),
                    },
                ),
            )

    @staticmethod
    def _unresolved_regex_count(series: pd.Series, *, column_name: str) -> int:
        values = series.fillna("")
        lowered = str(column_name).lower()
        if "email" in lowered:
            pattern = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
            invalid_mask = ~values.astype(str).str.fullmatch(pattern, na=False)
            return int(invalid_mask.sum())
        if any(token in lowered for token in ("phone", "mobile", "tel")):
            pattern = r"^\+?[\d\s().-]{7,}$"
            invalid_mask = ~values.astype(str).str.fullmatch(pattern, na=False)
            return int(invalid_mask.sum())
        return 0
