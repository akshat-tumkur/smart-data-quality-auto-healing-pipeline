class ValidationResult:
    def __init__(self, validator_name: str, status: bool, message: str = "", rows_affected: int = 0, execution_time: float = 0.0, metadata: dict = None):
        self.validator_name = validator_name
        self.status = status
        self.message = message
        self.rows_affected = rows_affected
        self.execution_time = execution_time
        self.metadata = metadata or {}
    def __str__(self):
        return f"ValidationResult(validator_name={self.validator_name}, status={self.status}, message={self.message}, rows_affected={self.rows_affected}, execution_time={self.execution_time})"
        