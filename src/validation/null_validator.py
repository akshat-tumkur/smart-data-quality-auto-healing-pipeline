from .base_validator import BaseValidator
from .validation_result import ValidationResult
import time

class NullValidator(BaseValidator):
    def __init__(self):
        super().__init__("NullValidator")

    def validate(self, df):
        start = time.perf_counter()
        null_counts = df.isnull().sum()
        null_counts = null_counts[null_counts > 0]
        rows_affected = null_counts.sum()
        status = rows_affected == 0
        if status:
            message = "No missing values found."
        else:
            message = f"Found {null_counts} null values across {df.shape[1]} coloumns"

        metadata = {
            "null_counts": null_counts.to_dict()
        }

        
        execution_time = time.perf_counter - start

        return ValidationResult(
            status=status,
            message=message,
            rows_affected=rows_affected,
            execution_time=execution_time,
            metadata=metadata
        )
