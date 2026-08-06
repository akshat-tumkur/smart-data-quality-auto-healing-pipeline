"""Schema validation orchestration entry point."""

from __future__ import annotations
from typing import Any

import pandas as pd

from .schema_validator import SchemaValidator
from .schema_result import SchemaResult


class SchemaManager:
    """Coordinate schema validation for a DataFrame."""

    def __init__(self, schema_validator: SchemaValidator) -> None:
        self.schema_validator = schema_validator

    def run_schema_validation(
        self,
        dataframe: pd.DataFrame,
        config: dict[str, Any] | None = None,
    ) -> SchemaResult:
        """Validate the provided DataFrame using the configured schema."""

        return self.schema_validator.validate(dataframe, config)
