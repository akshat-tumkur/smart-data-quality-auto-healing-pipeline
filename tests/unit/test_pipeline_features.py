import json

import pandas as pd

from core.pipeline import Pipeline
from profiling.dataset_profiler import DatasetProfiler
from profiling.profiling_manager import ProfilingManager
from schema.schema_manager import SchemaManager
from schema.schema_validator import SchemaValidator
from validation.validation_result import ValidationResult


class ValidationManager:
    def run_validations(self, dataframe):
        missing = int(dataframe["value"].isna().sum())
        return [
            ValidationResult(
                validator_name="Null Validator",
                status=missing == 0,
                rows_affected=missing,
                metadata={"validation_type": "missing"},
            )
        ]


class MissingValueManager:
    def heal(self, dataframe, validation_results=None):
        updated = dataframe.copy()
        updated["value"] = updated["value"].fillna(2)
        return updated, []


def schema_config():
    return {
        "allow_extra_columns": True,
        "columns": {
            "value": {"type": "numeric", "nullable": True},
        },
    }


def test_pipeline_integrates_quality_score_metrics_and_audit():
    pipeline = Pipeline(
        profiling_manager=ProfilingManager(DatasetProfiler()),
        validation_manager=ValidationManager(),
        healer_manager=MissingValueManager(),
        schema_manager=SchemaManager(SchemaValidator()),
        config={
            "dataset": {"path": "data/test.csv"},
            "schema": schema_config(),
            "quality_score": {
                "enabled": True,
                "weights": {
                    "completeness": 0.5,
                    "validity": 0.25,
                    "uniqueness": 0.25,
                },
            },
            "anomaly_detection": {"enabled": False},
        },
    )

    result = pipeline.run(pd.DataFrame({"value": [1, None, 2, 2]}))

    assert result.quality_score["enabled"] is True
    assert result.quality_score["final"]["score"] > result.quality_score["initial"]["score"]
    assert result.metrics["missing_values"] == {"before": 1, "after": 0, "delta": -1}
    assert len(result.audit_trail["healing_actions"]) == 0
    json.dumps(result.audit_trail)


def test_pipeline_anomaly_detection_is_optional_and_reportable():
    pipeline = Pipeline(
        profiling_manager=ProfilingManager(DatasetProfiler()),
        validation_manager=ValidationManager(),
        healer_manager=MissingValueManager(),
        schema_manager=SchemaManager(SchemaValidator()),
        config={
            "schema": schema_config(),
            "quality_score": {"enabled": False},
            "anomaly_detection": {
                "enabled": True,
                "method": "isolation_forest",
                "contamination": 0.25,
                "random_state": 42,
            },
        },
    )

    dataframe = pd.DataFrame({"value": [1, 2, 3, 100]})
    result = pipeline.run(dataframe)

    assert result.anomaly_detection_result is not None
    assert result.anomaly_detection_result.enabled is True
    assert result.anomaly_detection_result.anomaly_count >= 1
    assert dataframe.equals(pd.DataFrame({"value": [1, 2, 3, 100]}))