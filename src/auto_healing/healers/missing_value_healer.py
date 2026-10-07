"""Missing value healing plugin."""

from __future__ import annotations

from time import perf_counter
from typing import Any, Sequence

import pandas as pd

from auto_healing.base_healer import BaseHealer
from auto_healing.healing_result import HealingResult


class MissingValueHealer(BaseHealer):
    """Fill missing values using deterministic, column-aware strategies."""

    display_name = "Missing Value Healer"
    validation_types = frozenset({"missing"})

    def __init__(
        self,
        strategy: str = "mean",
        fill_value: Any = None,
        columns: Sequence[str] | None = None,
    ) -> None:
        """Initialize the healer with a fill strategy and optional columns."""

        self.strategy = strategy.lower().strip()
        self.fill_value = fill_value
        self.columns = list(columns) if columns is not None else None

    def heal(self, dataframe: pd.DataFrame) -> tuple[pd.DataFrame, HealingResult]:
        """Fill missing values and return the updated DataFrame and result."""

        start_time = perf_counter()

        try:
            if self.strategy not in {"mean", "median", "mode", "constant"}:
                raise ValueError(f"Unsupported missing value strategy: {self.strategy}")

            before_dataframe = dataframe.copy(deep=True)
            working_dataframe = dataframe.copy(deep=True)
            target_columns = self.columns or list(working_dataframe.columns)
            attempted = 0
            changed = 0
            unresolved = 0
            filled_columns: dict[str, dict[str, Any]] = {}
            skipped_columns: dict[str, str] = {}

            for column in target_columns:
                if column not in working_dataframe.columns:
                    skipped_columns[column] = "Column not found."
                    continue

                series = working_dataframe[column]
                missing_mask = series.isna()
                missing_count = int(missing_mask.sum())
                if missing_count == 0:
                    continue

                attempted += missing_count
                column_strategy = self.strategy
                if self.strategy == "constant":
                    if self.fill_value is None:
                        raise ValueError("Constant strategy requires a fill_value.")
                    fill_value = self.fill_value
                else:
                    if pd.api.types.is_numeric_dtype(series):
                        if self.strategy == "mean":
                            fill_value = series.mean(skipna=True)
                            column_strategy = "mean"
                        elif self.strategy == "median":
                            fill_value = series.median(skipna=True)
                            column_strategy = "median"
                        else:
                            mode_values = series.mode(dropna=True)
                            fill_value = mode_values.iloc[0] if not mode_values.empty else None
                            column_strategy = "mode"
                    else:
                        mode_values = series.mode(dropna=True)
                        fill_value = mode_values.iloc[0] if not mode_values.empty else None
                        column_strategy = "mode"

                if fill_value is None or pd.isna(fill_value):
                    skipped_columns[column] = "No deterministic fill value available."
                    unresolved += missing_count
                    continue

                working_dataframe[column] = series.fillna(fill_value)
                filled_columns[column] = {
                    "strategy": column_strategy,
                    "fill_value": fill_value,
                    "filled_count": missing_count,
                }
                changed += missing_count

            for column in filled_columns:
                dataframe[column] = working_dataframe[column]

            change_summary = self._change_summary(
                before_dataframe,
                dataframe,
                columns=list(filled_columns.keys()),
            )
            status, message = self.summarize_status(
                attempted=attempted,
                changed=changed,
                unresolved=unresolved,
                default_message=(
                    f"Filled {changed} missing values."
                    if changed > 0
                    else "No missing values were filled."
                ),
            )
            metadata = {
                "strategy": "per_column",
                "configured_strategy": self.strategy,
                "attempted": attempted,
                "changed": changed,
                "unresolved": unresolved,
                "rows_affected": change_summary["rows_affected"],
                "cells_changed": change_summary["cells_changed"],
                "columns_affected": change_summary["columns_affected"],
                "filled_columns": filled_columns,
                "skipped_columns": skipped_columns,
            }
            return (
                dataframe,
                self.build_result(
                    status=status,
                    message=message,
                    rows_affected=change_summary["rows_affected"],
                    execution_time=perf_counter() - start_time,
                    metadata=metadata,
                ),
            )
        except Exception as exc:
            return (
                dataframe,
                self.build_result(
                    status="failed",
                    message="Missing value healing failed.",
                    rows_affected=0,
                    execution_time=perf_counter() - start_time,
                    metadata={
                        "strategy": self.strategy,
                        "exception_type": type(exc).__name__,
                        "exception_message": str(exc),
                    },
                ),
            )