from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from config.config_loader import load_config
from ingestion.ingestion_manager import IngestionManager
from validation.validators.datatype_validator import DataTypeValidator
from validation.validators.duplicate_validator import DuplicateValidator
from validation.validators.null_validator import NullValidator
from validation.validators.regex_validator import RegexValidator
from profiling.dataset_profiler import DatasetProfiler
from validation.validator_manager import ValidatorManager
from profiling.profiling_manager import ProfilingManager
from core.pipeline import Pipeline
from auto_healing import (
    DatatypeHealer,
    DuplicateHealer,
    HealerManager,
    MissingValueHealer,
    RegexHealer,
)
from reporting.report_generator import ReportGenerator
from reporting.report_manager import ReportManager


def load_runtime_config() -> dict:
    config = load_config(str(PROJECT_ROOT / "config" / "pipeline_config.yaml"))
    validation_rules = load_config(str(PROJECT_ROOT / "config" / "validation_rules.yaml"))
    config["validation_rules"] = validation_rules.get("validation_rules", {})
    return config


def build_validators(config) -> list:
    validation_rules = config.get("validation_rules", {})
    validators = []

    null_rules = validation_rules.get("null", {})
    if null_rules.get("enabled", False):
        validators.append(NullValidator())

    duplicate_rules = validation_rules.get("duplicate", {})
    if duplicate_rules.get("enabled", False):
        validators.append(DuplicateValidator())

    for rule in validation_rules.get("regex", []):
        column_name = rule.get("column")
        pattern = rule.get("pattern")
        if column_name and pattern:
            validators.append(RegexValidator(column_name, pattern))

    for rule in validation_rules.get("datatype", []):
        column_name = rule.get("column")
        expected_type = rule.get("type")
        if column_name and expected_type:
            validators.append(DataTypeValidator(column_name, expected_type))

    return validators


def build_healers() -> HealerManager:
    """Build the default auto-healing plugin chain."""

    return HealerManager(
        [
            MissingValueHealer(),
            DuplicateHealer(),
            DatatypeHealer(),
            RegexHealer(),
        ]
    )


def main() -> None:
    try:
        config = load_runtime_config()

        ingestion_manager = IngestionManager(config)
        data = ingestion_manager.ingest()
        profiler = DatasetProfiler()
        profiling_manager = ProfilingManager(profiler=profiler)
        validators = build_validators(config)
        validator_manager = ValidatorManager(validators=validators)
        healer_manager = build_healers()
        pipeline = Pipeline(
            profiling_manager=profiling_manager,
            validation_manager=validator_manager,
            healer_manager=healer_manager,
        )
        pipeline_result = pipeline.run(data)

        generator = ReportGenerator()
        manager = ReportManager(generator)
        report = manager.generate_report(pipeline_result)
        saved_path = manager.save(report)

        profile_result = pipeline_result.profile_result
        validation_results = pipeline_result.validation_results
        healing_results = pipeline_result.healing_results
        passed = sum(1 for result in validation_results if bool(getattr(result, "status", False)))
        failed = len(validation_results) - passed
        healed_success = sum(1 for result in healing_results if getattr(result, "status", "") == "success")
        healed_failed = len(healing_results) - healed_success

        print("========================================")
        print("SMART DATA QUALITY PIPELINE COMPLETED")
        print("========================================")
        print()
        print(f"Dataset Rows      : {getattr(profile_result, 'row_count', 0)}")
        print(f"Dataset Columns   : {getattr(profile_result, 'column_count', 0)}")
        print()
        print(f"Validators Run    : {len(validation_results)}")
        print(f"Passed            : {passed}")
        print(f"Failed            : {failed}")
        print()
        print(f"Healers Run       : {len(healing_results)}")
        print(f"Succeeded         : {healed_success}")
        print(f"Failed            : {healed_failed}")
        print()
        print("Report saved to:")
        print()
        print(saved_path)
    except Exception as exc:
        print(f"Pipeline execution failed: {exc}")
        raise


if __name__ == "__main__":
    main()