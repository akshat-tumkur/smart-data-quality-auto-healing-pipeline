from ..base_validator import BaseValidator
from ..validation_result import ValidationResult
import time

class RegexValidator(BaseValidator):
    def __init__(self, column_name, pattern):
        super().__init__("Regex Validator")
        self.column_name = column_name
        self.pattern = pattern

    def validate(self, df):
        start = time.perf_counter()
        if self.column_name not in df.columns:
            raise ValueError(f"Column '{self.column_name}' does not exist in the DataFrame.")

        invalid_rows = ~df[self.column_name].astype(str).str.match(self.pattern)
        rows_affected = invalid_rows.sum()
        status = rows_affected == 0
        if status:
            message = f"All values in column '{self.column_name}' match the regex pattern."
        else:
            message = f"Found {rows_affected} rows in column '{self.column_name}' that do not match the regex pattern."

        metadata = {
            "invalid_indices": df[invalid_rows].index.tolist()
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