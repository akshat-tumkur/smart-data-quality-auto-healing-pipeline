"""Result container for dataset profiling."""


class ProfileResult:
    """Store the output of a dataset profiling run."""

    def __init__(
        self,
        dataset_name: str = "dataset",
        row_count: int = 0,
        column_count: int = 0,
        duplicate_rows: int = 0,
        total_missing_values: int = 0,
        missing_values_per_column: dict | None = None,
        data_types: dict | None = None,
        numeric_summary: dict | None = None,
        categorical_summary: dict | None = None,
        memory_usage: int = 0,
        execution_time: float = 0.0,
    ) -> None:
        self.dataset_name = dataset_name
        self.row_count = row_count
        self.column_count = column_count
        self.duplicate_rows = duplicate_rows
        self.total_missing_values = total_missing_values
        self.missing_values_per_column = missing_values_per_column or {}
        self.data_types = data_types or {}
        self.numeric_summary = numeric_summary or {}
        self.categorical_summary = categorical_summary or {}
        self.memory_usage = memory_usage
        self.execution_time = execution_time

    def __repr__(self) -> str:
        return (
            "ProfileResult(dataset_name="
            f"{self.dataset_name!r}, row_count={self.row_count}, "
            f"column_count={self.column_count}, duplicate_rows={self.duplicate_rows}, "
            f"total_missing_values={self.total_missing_values})"
        )
