import pandas as pd

from schema.schema_manager import SchemaManager
from schema.schema_result import SchemaResult
from schema.schema_validator import SchemaValidator
from core.pipeline import Pipeline


def make_validation_config() -> dict:
    return {
        "datatype": {
            "enabled": True,
            "columns": {
                "salary": "numeric",
                "performance_rating": "int",
            },
        },
        "regex": [
            {"column": "email", "pattern": "EMAIL"},
        ],
        "duplicate": {
            "enabled": True,
            "subset": ["salary", "performance_rating"],
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
    result = validator.validate(dataframe, make_validation_config())

    assert isinstance(result, SchemaResult)
    assert result.status is True
    assert result.missing_columns == []
    assert result.unexpected_columns == []
    assert result.datatype_mismatches == {}
    assert "Schema validation passed." in result.message


def test_schema_validator_missing_configured_columns():
    dataframe = pd.DataFrame(
        {
            "performance_rating": [1, 2],
            "email": ["a@example.com", "b@example.com"],
        }
    )

    validator = SchemaValidator()
    result = validator.validate(dataframe, make_validation_config())

    assert result.status is False
    assert result.missing_columns == ["salary"]
    assert result.unexpected_columns == []
    assert result.datatype_mismatches == {}
    assert "Missing required columns" in result.message


def test_schema_validator_unexpected_columns():
    dataframe = pd.DataFrame(
        {
            "salary": [1000.0, 2000.5],
            "performance_rating": [1, 2],
            "email": ["a@example.com", "b@example.com"],
            "extra": ["x", "y"],
        }
    )

    validator = SchemaValidator()
    result = validator.validate(dataframe, make_validation_config())

    assert result.status is True
    assert result.missing_columns == []
    assert result.unexpected_columns == ["extra"]
    assert result.datatype_mismatches == {}
    assert "Unexpected columns" in result.message


def test_schema_validator_datatype_mismatch():
    dataframe = pd.DataFrame(
        {
            "salary": ["not-a-number", "2000"],
            "performance_rating": [1, 2],
            "email": ["a@example.com", "b@example.com"],
        }
    )

    validator = SchemaValidator()
    result = validator.validate(dataframe, make_validation_config())

    assert result.status is False
    assert result.missing_columns == []
    assert result.unexpected_columns == []
    assert "salary" in result.datatype_mismatches
    assert result.datatype_mismatches["salary"]["expected"] == "numeric"
    assert result.datatype_mismatches["salary"]["actual"] == "object"
    assert "Datatype mismatches" in result.message


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
        config={"validation": make_validation_config()},
    )

    result = pipeline.run(dataframe)

    assert result.initial_schema_result is not None
    assert result.initial_schema_result.missing_columns == ["salary"]
    assert result.initial_profile is None
    assert result.initial_validation == []
    assert result.healing_results == []
    assert result.final_validation == []
