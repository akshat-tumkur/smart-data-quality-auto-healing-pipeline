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

    def validate(
        self,
        dataframe: pd.DataFrame,
        config: dict[str, Any] | None = None,
    ) -> SchemaResult:
        """Validate the supplied DataFrame and return a SchemaResult."""

        start = time.perf_counter()
        schema_config = config or {}
        allow_extra_columns = bool(schema_config.get("allow_extra_columns", True))
        configured_columns = schema_config.get("columns", {})

        if not isinstance(configured_columns, dict):
            configured_columns = {}

        required_columns = set(configured_columns.keys())

        missing_columns = [column for column in sorted(required_columns) if column not in dataframe.columns]
        unexpected_columns = [
            column for column in list(dataframe.columns) if column not in required_columns
        ]

        datatype_mismatches: dict[str, dict[str, str]] = {}
        nullable_violations: dict[str, dict[str, int | bool]] = {}
        for column, definition in configured_columns.items():
            if column not in dataframe.columns:
                continue

            expected_type = self._extract_expected_type(definition)
            nullable = self._extract_nullable(definition)

            actual_dtype = dataframe[column].dtype
            if not self._matches_expected_dtype(actual_dtype, expected_type):
                datatype_mismatches[column] = {
                    "expected": expected_type,
                    "actual": actual_dtype.name,
                }

            if not nullable:
                null_count = int(dataframe[column].isna().sum())
                if null_count > 0:
                    nullable_violations[column] = {
                        "nullable": False,
                        "null_count": null_count,
                    }

        has_unexpected_column_failure = (not allow_extra_columns) and bool(unexpected_columns)
        status = (
            not missing_columns
            and not bool(datatype_mismatches)
            and not bool(nullable_violations)
            and not has_unexpected_column_failure
        )
        message = self._build_message(
            missing_columns,
            unexpected_columns,
            datatype_mismatches,
            nullable_violations,
            allow_extra_columns,
        )
        execution_time = time.perf_counter() - start
        metadata = {
            "allow_extra_columns": allow_extra_columns,
            "required_columns": sorted(required_columns),
            "missing_columns": missing_columns,
            "unexpected_columns": unexpected_columns,
            "datatype_mismatches": datatype_mismatches,
            "nullable_violations": nullable_violations,
        }

        return SchemaResult(
            status=status,
            message=message,
            missing_columns=missing_columns,
            unexpected_columns=unexpected_columns,
            datatype_mismatches=datatype_mismatches,
            nullable_violations=nullable_violations,
            execution_time=execution_time,
            metadata=metadata,
        )

    def _extract_expected_type(self, definition: Any) -> str:
        if isinstance(definition, dict):
            return str(definition.get("type", ""))
        return str(definition)

    def _extract_nullable(self, definition: Any) -> bool:
        if isinstance(definition, dict):
            return bool(definition.get("nullable", True))
        return True

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
        nullable_violations: dict[str, dict[str, int | bool]],
        allow_extra_columns: bool,
    ) -> str:
        if missing_columns:
            return f"Missing required columns: {', '.join(missing_columns)}."

        details: list[str] = []
        if unexpected_columns:
            suffix = "(allowed)" if allow_extra_columns else "(not allowed)"
            details.append(
                f"Unexpected columns {suffix}: {', '.join(unexpected_columns)}."
            )
        if datatype_mismatches:
            mismatch_strings = [
                f"{column} expected={mismatch['expected']} actual={mismatch['actual']}"
                for column, mismatch in datatype_mismatches.items()
            ]
            details.append(f"Datatype mismatches: {'; '.join(mismatch_strings)}.")
        if nullable_violations:
            violation_strings = [
                f"{column} null_count={violation['null_count']}"
                for column, violation in nullable_violations.items()
            ]
            details.append(f"Nullable violations: {'; '.join(violation_strings)}.")

        return " ".join(details) if details else "Schema validation passed."
