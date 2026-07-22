import pandas as pd

from src.profiling import DatasetProfiler, ProfileResult, ProfilingManager


def test_profile_returns_summary_without_mutating_dataframe():
    dataframe = pd.DataFrame(
        {
            "name": ["Alice", "Bob", "Alice"],
            "age": [20, 30, 20],
            "score": [1.0, None, 3.0],
        }
    )
    original_copy = dataframe.copy(deep=True)

    profiler = DatasetProfiler()
    result = profiler.profile(dataframe)

    assert isinstance(result, ProfileResult)
    assert result.dataset_name == "dataset"
    assert result.row_count == 3
    assert result.column_count == 3
    assert result.duplicate_rows == 1
    assert result.total_missing_values == 1
    assert result.missing_values_per_column["score"] == 1
    assert result.data_types["age"] == "int64"
    assert "age" in result.numeric_summary
    assert "name" in result.categorical_summary
    assert dataframe.equals(original_copy)


def test_manager_delegates_to_profiler():
    dataframe = pd.DataFrame({"value": [1, 2, 3]})

    class DummyProfiler:
        def profile(self, frame):
            return ProfileResult("dummy", row_count=len(frame), column_count=len(frame.columns))

    manager = ProfilingManager(DummyProfiler())
    result = manager.run_profiling(dataframe)

    assert isinstance(result, ProfileResult)
    assert result.dataset_name == "dummy"
    assert result.row_count == 3
