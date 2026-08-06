"""Schema validation helpers."""

from __future__ import annotations

import time
from typing import Any

import pandas as pd
from pandas.api import types as pd_types

from .schema_result import SchemaResult


class SchemaValidator:
    """Validate a DataFrame against configured schema expectations."""

    def __init__(self, validator_name: str = "Schema Validator") -> None:
        self.validator_name = validator_name

    def validate(self, dataframe: pd.DataFrame, config: dict[str, Any] | None = None) -> SchemaResult:
        """Validate the supplied DataFrame and return a SchemaResult."""

        start = time.perf_counter()
        validation_config = config or {}

        datatype_config = validation_config.get("datatype", {})
        regex_config = validation_config.get("regex", [])
        duplicate_config = validation_config.get("duplicate", {})

        datatype_columns: dict[str, Any] = {}
        if isinstance(datatype_config, list):
            datatype_columns = {
                rule.get("column"): rule.get("type")
                for rule in datatype_config
                if isinstance(rule, dict) and rule.get("column") and rule.get("type")
            }
        elif isinstance(datatype_config, dict):
            datatype_columns = dict(datatype_config.get("columns", {}))

        required_columns = set(datatype_columns.keys())

        if isinstance(regex_config, list):
            required_columns.update(
                rule["column"]
                for rule in regex_config
                if isinstance(rule, dict) and rule.get("column")
            )

        duplicate_subset = duplicate_config.get("subset")
        if duplicate_subset is not None:
            if isinstance(duplicate_subset, list):
                required_columns.update(duplicate_subset)
            else:
                required_columns.add(duplicate_subset)

        missing_columns = [column for column in sorted(required_columns) if column not in dataframe.columns]
        unexpected_columns = [column for column in list(dataframe.columns) if column not in required_columns]

        datatype_mismatches: dict[str, dict[str, str]] = {}
        for column, expected_type in datatype_columns.items():
            if column not in dataframe.columns:
                continue

            actual_dtype = dataframe[column].dtype
            if not self._matches_expected_dtype(actual_dtype, expected_type):
                datatype_mismatches[column] = {
                    "expected": expected_type,
                    "actual": actual_dtype.name,
                }

        status = not missing_columns and not bool(datatype_mismatches)
        message = self._build_message(missing_columns, unexpected_columns, datatype_mismatches)
        execution_time = time.perf_counter() - start
        metadata = {
            "required_columns": sorted(required_columns),
            "missing_columns": missing_columns,
            "unexpected_columns": unexpected_columns,
            "datatype_mismatches": datatype_mismatches,
        }

        return SchemaResult(
            status=status,
            message=message,
            missing_columns=missing_columns,
            unexpected_columns=unexpected_columns,
            datatype_mismatches=datatype_mismatches,
            execution_time=execution_time,
            metadata=metadata,
        )

    def _matches_expected_dtype(self, dtype: Any, expected_type: Any) -> bool:
        expected = str(expected_type).lower()

        if expected in ["int", "integer"]:
            return pd_types.is_integer_dtype(dtype)

        if expected in ["float"]:
            return pd_types.is_float_dtype(dtype)

        if expected in ["numeric", "number"]:
            return pd_types.is_numeric_dtype(dtype)

        if expected in ["string", "str"]:
            return pd_types.is_string_dtype(dtype) or pd_types.is_object_dtype(dtype)

        if expected in ["datetime", "timestamp"]:
            return pd_types.is_datetime64_any_dtype(dtype)

        return False

    def _build_message(
        self,
        missing_columns: list[str],
        unexpected_columns: list[str],
        datatype_mismatches: dict[str, dict[str, str]],
    ) -> str:
        if missing_columns:
            return f"Missing required columns: {', '.join(missing_columns)}."

        details: list[str] = []
        if unexpected_columns:
            details.append(f"Unexpected columns: {', '.join(unexpected_columns)}.")
        if datatype_mismatches:
            mismatch_strings = [
                f"{column} expected={mismatch['expected']} actual={mismatch['actual']}"
                for column, mismatch in datatype_mismatches.items()
            ]
            details.append(f"Datatype mismatches: {'; '.join(mismatch_strings)}.")

        return " ".join(details) if details else "Schema validation passed."
