"""Profiling utilities for pandas DataFrames."""

from __future__ import annotations

import time

import pandas as pd

from .profile_result import ProfileResult


class DatasetProfiler:
    """Generate descriptive statistics for a pandas DataFrame."""

    def profile(self, dataframe: pd.DataFrame) -> ProfileResult:
        """Profile a DataFrame without modifying it."""
        start_time = time.perf_counter()

        row_count = int(dataframe.shape[0])
        column_count = int(dataframe.shape[1])
        duplicate_rows = int(dataframe.duplicated().sum())
        missing_values_per_column = {
            column_name: int(count)
            for column_name, count in dataframe.isna().sum().items()
        }
        total_missing_values = int(sum(missing_values_per_column.values()))
        data_types = {column_name: str(dtype) for column_name, dtype in dataframe.dtypes.items()}
        memory_usage = int(dataframe.memory_usage(deep=True).sum())

        numeric_columns = dataframe.select_dtypes(include="number").columns
        categorical_columns = dataframe.select_dtypes(exclude="number").columns

        numeric_summary = {
            column_name: dataframe[column_name].describe().to_dict()
            for column_name in numeric_columns
        }
        categorical_summary = {
            column_name: dataframe[column_name].describe().to_dict()
            for column_name in categorical_columns
        }

        execution_time = time.perf_counter() - start_time

        return ProfileResult(
            dataset_name=getattr(dataframe, "name", "dataset"),
            row_count=row_count,
            column_count=column_count,
            duplicate_rows=duplicate_rows,
            total_missing_values=total_missing_values,
            missing_values_per_column=missing_values_per_column,
            data_types=data_types,
            numeric_summary=numeric_summary,
            categorical_summary=categorical_summary,
            memory_usage=memory_usage,
            execution_time=execution_time,
        )
