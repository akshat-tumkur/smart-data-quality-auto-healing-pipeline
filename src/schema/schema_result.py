"""Schema validation result container."""

from __future__ import annotations

from typing import Any


class SchemaResult:
    """Store the output of schema validation."""

    def __init__(
        self,
        status: bool,
        message: str = "",
        missing_columns: list[str] | None = None,
        unexpected_columns: list[str] | None = None,
        datatype_mismatches: dict[str, dict[str, str]] | None = None,
        execution_time: float = 0.0,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.status = status
        self.message = message
        self.missing_columns = missing_columns or []
        self.unexpected_columns = unexpected_columns or []
        self.datatype_mismatches = datatype_mismatches or {}
        self.execution_time = execution_time
        self.metadata = metadata or {}

    def __str__(self) -> str:
        lines = [
            f"status={self.status}",
            f"message={self.message}",
            f"missing_columns={self.missing_columns}",
            f"unexpected_columns={self.unexpected_columns}",
            f"datatype_mismatches={self.datatype_mismatches}",
            f"execution_time={self.execution_time}",
            f"metadata={self.metadata}",
        ]
        return "SchemaResult(" + ", ".join(lines) + ")"
