from ..base_validator import BaseValidator
from ..validation_result import ValidationResult
import time

class DuplicateValidator(BaseValidator):
    def __init__(self):
        super().__init__("Duplicate Validator")
    
    def validate(self, df):
        start = time.perf_counter()
        duplicate_rows = df.duplicated(keep=False)
        rows_affected = duplicate_rows.sum()
        status = rows_affected == 0
        if status:
            message = "No duplicate rows found."
        else:
            message = f"Found {rows_affected} duplicate rows."

        metadata = {
        "duplicate_indices": df[duplicate_rows].index.tolist()
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