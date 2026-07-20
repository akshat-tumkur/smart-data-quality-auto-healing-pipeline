from ..base_validator import BaseValidator
from ..validation_result import ValidationResult

import pandas as pd
import time


class DataTypeValidator(BaseValidator):

    def __init__(self, column_name, expected_type):
        super().__init__("Data Type Validator")
        self.column_name = column_name
        self.expected_type = expected_type.lower()

    def validate(self, df):

        start = time.perf_counter()

        if self.column_name not in df.columns:
            raise ValueError(
                f"Column '{self.column_name}' does not exist."
            )

        column = df[self.column_name]

        if self.expected_type in ["int", "integer", "float", "numeric"]:
            converted = pd.to_numeric(column, errors="coerce")

        elif self.expected_type == "datetime":
            converted = pd.to_datetime(column, errors="coerce")

        elif self.expected_type == "string":
            converted = column.astype(str)

        else:
            raise ValueError(
                f"Unsupported expected type: {self.expected_type}"
            )

        invalid_mask = converted.isna() & column.notna()
        rows_affected = invalid_mask.sum()
        status = rows_affected == 0

        if status:
            message = (
                f"All values in '{self.column_name}' "
                f"can be interpreted as {self.expected_type}."
            )

        else:
            message = (
                f"Found {rows_affected} invalid value(s) "
                f"in '{self.column_name}'."
            )

        metadata = {
            "column": self.column_name,
            "expected_type": self.expected_type,
            "invalid_indices": df[invalid_mask].index.tolist()
        }

        execution_time = time.perf_counter() - start

        return ValidationResult(
            validator_name=self.validator_name,
            status=status,
            message=message,
            rows_affected=rows_affected,
            execution_time=execution_time,
            metadata=metadata
        )