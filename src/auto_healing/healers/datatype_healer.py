"""Datatype conversion healing plugin."""

from __future__ import annotations

from time import perf_counter
from typing import Any, Mapping

import pandas as pd

from auto_healing.base_healer import BaseHealer
from auto_healing.healing_result import HealingResult


class DatatypeHealer(BaseHealer):
    """Convert configured columns using safe, loss-aware transformations."""

    display_name = "Datatype Healer"

    def __init__(self, column_types: Mapping[str, str] | None = None) -> None:
        """Initialize the healer with a mapping of column names to target types."""

        self.column_types = {
            column: target_type.lower().strip()
            for column, target_type in (column_types or {}).items()
        }

    def heal(self, dataframe: pd.DataFrame) -> tuple[pd.DataFrame, HealingResult]:
        """Convert configured columns and return the updated DataFrame and result."""

        start_time = perf_counter()

        try:
            working_dataframe = dataframe
            rows_affected = 0
            converted_columns: dict[str, dict[str, Any]] = {}
            failed_conversions: dict[str, dict[str, Any]] = {}
            skipped_columns: dict[str, str] = {}

            for column, target_type in self.column_types.items():
                if column not in working_dataframe.columns:
                    skipped_columns[column] = "Column not found."
                    continue

                series = working_dataframe[column]
                try:
                    converted_series, affected_rows, column_metadata = self._convert_series(
                        series=series,
                        target_type=target_type,
                    )
                except Exception as exc:
                    failed_conversions[column] = {
                        "target_type": target_type,
                        "exception_type": type(exc).__name__,
                        "exception_message": str(exc),
                    }
                    continue

                working_dataframe[column] = converted_series
                rows_affected += affected_rows
                if column_metadata.get("invalid_conversion_count", 0) > 0:
                    failed_conversions[column] = column_metadata
                else:
                    converted_columns[column] = column_metadata

            message = (
                f"Converted {rows_affected} values across {len(converted_columns)} columns."
                if rows_affected > 0
                else "No datatype conversions were applied."
            )
            metadata = {
                "converted_columns": converted_columns,
                "failed_conversions": failed_conversions,
                "skipped_columns": skipped_columns,
            }
            return (
                working_dataframe,
                self.build_result(
                    status="success",
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
                    message="Datatype healing failed.",
                    rows_affected=0,
                    execution_time=perf_counter() - start_time,
                    metadata={
                        "exception_type": type(exc).__name__,
                        "exception_message": str(exc),
                    },
                ),
            )

    def _convert_series(
        self,
        *,
        series: pd.Series,
        target_type: str,
    ) -> tuple[pd.Series, int, dict[str, Any]]:
        """Convert a series without silently dropping invalid data."""

        if target_type == "string":
            converted_series = series.astype("string")
            affected_rows = int(series.notna().sum())
            return converted_series, affected_rows, {
                "target_type": target_type,
                "invalid_conversion_count": 0,
            }

        if target_type in {"int", "float"}:
            numeric_series = pd.to_numeric(series, errors="coerce")
            non_missing_mask = series.notna()
            valid_mask = non_missing_mask & numeric_series.notna()

            if target_type == "int":
                integer_like_mask = valid_mask & (numeric_series % 1 == 0)
                invalid_mask = non_missing_mask & ~integer_like_mask
                if invalid_mask.any():
                    converted_series = series.copy(deep=True).astype(object)
                    converted_series.loc[integer_like_mask] = numeric_series.loc[
                        integer_like_mask
                    ].astype("int64")
                    return converted_series, int(integer_like_mask.sum()), {
                        "target_type": target_type,
                        "invalid_conversion_count": int(invalid_mask.sum()),
                        "invalid_rows": series.index[invalid_mask].tolist(),
                        "invalid_values_sample": series[invalid_mask].astype(str).head(10).tolist(),
                    }

                converted_series = numeric_series.astype("Int64")
                return converted_series, int(integer_like_mask.sum()), {
                    "target_type": target_type,
                    "invalid_conversion_count": 0,
                }

            invalid_mask = non_missing_mask & numeric_series.isna()
            if invalid_mask.any():
                converted_series = series.copy(deep=True).astype(object)
                converted_series.loc[valid_mask] = numeric_series.loc[valid_mask].astype(
                    "float64"
                )
                return converted_series, int(valid_mask.sum()), {
                    "target_type": target_type,
                    "invalid_conversion_count": int(invalid_mask.sum()),
                    "invalid_rows": series.index[invalid_mask].tolist(),
                    "invalid_values_sample": series[invalid_mask].astype(str).head(10).tolist(),
                }

            converted_series = numeric_series.astype("Float64")
            return converted_series, int(valid_mask.sum()), {
                "target_type": target_type,
                "invalid_conversion_count": 0,
            }

        if target_type == "datetime":
            datetime_series = pd.to_datetime(series, errors="coerce")
            non_missing_mask = series.notna()
            valid_mask = non_missing_mask & datetime_series.notna()
            invalid_mask = non_missing_mask & datetime_series.isna()

            if invalid_mask.any():
                converted_series = series.copy(deep=True).astype(object)
                converted_series.loc[valid_mask] = datetime_series.loc[valid_mask]
                return converted_series, int(valid_mask.sum()), {
                    "target_type": target_type,
                    "invalid_conversion_count": int(invalid_mask.sum()),
                    "invalid_rows": series.index[invalid_mask].tolist(),
                    "invalid_values_sample": series[invalid_mask].astype(str).head(10).tolist(),
                }

            return datetime_series, int(valid_mask.sum()), {
                "target_type": target_type,
                "invalid_conversion_count": 0,
            }

        raise ValueError(f"Unsupported target type: {target_type}")