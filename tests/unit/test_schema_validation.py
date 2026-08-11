import pandas as pd

from core.pipeline import Pipeline
from schema.schema_manager import SchemaManager
from schema.schema_result import SchemaResult
from schema.schema_validator import SchemaValidator


def make_schema_config(*, allow_extra_columns: bool = True) -> dict:
    return {
        "allow_extra_columns": allow_extra_columns,
        "columns": {
            "salary": {
                "type": "numeric",
                "nullable": False,
            },
            "performance_rating": {
                "type": "int",
                "nullable": True,
            },
            "email": {
                "type": "string",
                "nullable": False,
            },
        },
    }


def test_schema_validator_valid_schema():
    dataframe = pd.DataFrame(
        {
            "salary": [1000.0, 2000.5],
            "performance_rating": [1, 2],
            "email": ["a@example.com", "b@example.com"],
        }
    )

    validator = SchemaValidator()
    result = validator.validate(dataframe, make_schema_config())

    assert isinstance(result, SchemaResult)
    assert result.status is True
    assert result.missing_columns == []
    assert result.unexpected_columns == []
    assert result.datatype_mismatches == {}
    assert result.nullable_violations == {}
    assert "Schema validation passed." in result.message


def test_schema_validator_missing_required_column():
    dataframe = pd.DataFrame(
        {
            "performance_rating": [1, 2],
            "email": ["a@example.com", "b@example.com"],
        }
    )

    validator = SchemaValidator()
    result = validator.validate(dataframe, make_schema_config())

    assert result.status is False
    assert result.missing_columns == ["salary"]
    assert result.unexpected_columns == []
    assert result.datatype_mismatches == {}
    assert result.nullable_violations == {}
    assert "Missing required columns" in result.message


def test_schema_validator_unexpected_column_allowed():
    dataframe = pd.DataFrame(
        {
            "salary": [1000.0, 2000.5],
            "performance_rating": [1, 2],
            "email": ["a@example.com", "b@example.com"],
            "extra": ["x", "y"],
        }
    )

    validator = SchemaValidator()
    result = validator.validate(dataframe, make_schema_config(allow_extra_columns=True))

    assert result.status is True
    assert result.missing_columns == []
    assert result.unexpected_columns == ["extra"]
    assert result.datatype_mismatches == {}
    assert result.nullable_violations == {}
    assert "Unexpected columns" in result.message
    assert "allowed" in result.message


def test_schema_validator_unexpected_column_not_allowed():
    dataframe = pd.DataFrame(
        {
            "salary": [1000.0, 2000.5],
            "performance_rating": [1, 2],
            "email": ["a@example.com", "b@example.com"],
            "extra": ["x", "y"],
        }
    )

    validator = SchemaValidator()
    result = validator.validate(dataframe, make_schema_config(allow_extra_columns=False))

    assert result.status is False
    assert result.missing_columns == []
    assert result.unexpected_columns == ["extra"]
    assert result.datatype_mismatches == {}
    assert result.nullable_violations == {}
    assert "Unexpected columns" in result.message
    assert "not allowed" in result.message


def test_schema_validator_datatype_mismatch():
    dataframe = pd.DataFrame(
        {
            "salary": ["not-a-number", "2000"],
            "performance_rating": [1, 2],
            "email": ["a@example.com", "b@example.com"],
        }
    )

    validator = SchemaValidator()
    result = validator.validate(dataframe, make_schema_config())

    assert result.status is False
    assert result.missing_columns == []
    assert result.unexpected_columns == []
    assert "salary" in result.datatype_mismatches
    assert result.datatype_mismatches["salary"]["expected"] == "numeric"
    assert result.datatype_mismatches["salary"]["actual"] == "object"
    assert result.nullable_violations == {}
    assert "Datatype mismatches" in result.message


def test_schema_validator_non_nullable_column_with_nulls_fails():
    dataframe = pd.DataFrame(
        {
            "salary": [1000.0, None],
            "performance_rating": [1, 2],
            "email": ["a@example.com", "b@example.com"],
        }
    )

    validator = SchemaValidator()
    result = validator.validate(dataframe, make_schema_config())

    assert result.status is False
    assert result.missing_columns == []
    assert result.unexpected_columns == []
    assert result.datatype_mismatches == {}
    assert result.nullable_violations["salary"]["null_count"] == 1
    assert "Nullable violations" in result.message


def test_schema_validator_nullable_column_with_nulls_passes():
    dataframe = pd.DataFrame(
        {
            "salary": [1000.0, 2000.5],
            "performance_rating": pd.Series([1, None], dtype="Int64"),
            "email": ["a@example.com", "b@example.com"],
        }
    )

    validator = SchemaValidator()
    result = validator.validate(dataframe, make_schema_config())

    assert result.status is True
    assert result.missing_columns == []
    assert result.unexpected_columns == []
    assert result.datatype_mismatches == {}
    assert result.nullable_violations == {}


def test_schema_validator_does_not_derive_columns_from_validation_rules():
    dataframe = pd.DataFrame({"salary": [1000.0], "email": ["a@example.com"]})

    schema_config = {
        "allow_extra_columns": True,
        "columns": {
            "salary": {"type": "numeric", "nullable": False},
            "email": {"type": "string", "nullable": False},
        },
        "validation": {
            "regex": [{"column": "should_not_be_required", "pattern": "EMAIL"}],
            "duplicate": {"subset": ["also_not_required"]},
            "datatype": {"columns": {"another": "int"}},
        },
    }

    validator = SchemaValidator()
    result = validator.validate(dataframe, schema_config)

    assert result.status is True
    assert result.missing_columns == []
    assert "should_not_be_required" not in result.metadata.get("required_columns", [])
    assert "also_not_required" not in result.metadata.get("required_columns", [])


def test_pipeline_stops_when_required_columns_missing():
    dataframe = pd.DataFrame(
        {
            "performance_rating": [1, 2],
            "email": ["a@example.com", "b@example.com"],
        }
    )

    class DummyProfiler:
        def profile(self, frame):
            raise AssertionError("Profiler should not run when schema is missing required columns")

    class DummyValidatorManager:
        def run_validations(self, frame):
            raise AssertionError("Validation should not run when schema is missing required columns")

    class DummyHealerManager:
        def heal(self, frame):
            raise AssertionError("Healing should not run when schema is missing required columns")

    schema_manager = SchemaManager(SchemaValidator())
    pipeline = Pipeline(
        profiling_manager=DummyProfiler(),
        validation_manager=DummyValidatorManager(),
        healer_manager=DummyHealerManager(),
        schema_manager=schema_manager,
        config={"schema": make_schema_config()},
    )

    result = pipeline.run(dataframe)

    assert result.initial_schema_result is not None
    assert result.initial_schema_result.missing_columns == ["salary"]
    assert result.initial_profile is None
    assert result.initial_validation == []
    assert result.healing_results == []
    assert result.final_validation == []


def test_pipeline_continues_when_schema_has_non_missing_violations():
    dataframe = pd.DataFrame(
        {
            "salary": ["bad-salary", "2000"],
            "performance_rating": [1, 2],
            "email": ["a@example.com", "b@example.com"],
        }
    )

    call_counts = {
        "profiling": 0,
        "validation": 0,
        "healing": 0,
    }

    class DummyProfiler:
        def run_profiling(self, frame):
            call_counts["profiling"] += 1
            return object()

    class DummyValidatorManager:
        def run_validations(self, frame):
            call_counts["validation"] += 1
            return []

    class DummyHealerManager:
        def heal(self, frame):
            call_counts["healing"] += 1
            return frame, []

    schema_manager = SchemaManager(SchemaValidator())
    pipeline = Pipeline(
        profiling_manager=DummyProfiler(),
        validation_manager=DummyValidatorManager(),
        healer_manager=DummyHealerManager(),
        schema_manager=schema_manager,
        config={"schema": make_schema_config()},
    )

    result = pipeline.run(dataframe)

    assert result.initial_schema_result is not None
    assert result.initial_schema_result.missing_columns == []
    assert result.initial_schema_result.status is False
    assert "salary" in result.initial_schema_result.datatype_mismatches
    assert call_counts["profiling"] == 2
    assert call_counts["validation"] == 2
    assert call_counts["healing"] == 1


def test_pipeline_existing_behavior_with_valid_schema():
    dataframe = pd.DataFrame(
        {
            "salary": [1000.0, 2000.5],
            "performance_rating": [1, 2],
            "email": ["a@example.com", "b@example.com"],
        }
    )

    call_counts = {
        "profiling": 0,
        "validation": 0,
        "healing": 0,
    }

    class DummyProfiler:
        def run_profiling(self, frame):
            call_counts["profiling"] += 1
            return object()

    class DummyValidatorManager:
        def run_validations(self, frame):
            call_counts["validation"] += 1
            return []

    class DummyHealerManager:
        def heal(self, frame):
            call_counts["healing"] += 1
            return frame, []

    pipeline = Pipeline(
        profiling_manager=DummyProfiler(),
        validation_manager=DummyValidatorManager(),
        healer_manager=DummyHealerManager(),
        schema_manager=SchemaManager(SchemaValidator()),
        config={"schema": make_schema_config()},
    )

    result = pipeline.run(dataframe)

    assert result.initial_schema_result is not None
    assert result.initial_schema_result.status is True
    assert result.initial_schema_result.missing_columns == []
    assert call_counts["profiling"] == 2
    assert call_counts["validation"] == 2
    assert call_counts["healing"] == 1
