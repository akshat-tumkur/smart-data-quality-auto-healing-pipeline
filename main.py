from pathlib import Path
import sys

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from config.config_loader import load_application_config
from ingestion.ingestion_manager import IngestionManager
from profiling.dataset_profiler import DatasetProfiler
from validation.validator_manager import ValidatorManager
from profiling.profiling_manager import ProfilingManager
from core.pipeline import Pipeline
from auto_healing import HealerManager
from auto_healing.healer_factory import HealerFactory
from reporting.report_generator import ReportGenerator
from reporting.report_manager import ReportManager
from validation.validator_factory import ValidatorFactory


def load_runtime_config() -> dict:
    return load_application_config()


def build_cleaned_dataset_path(
    config: dict,
    output_directory: Path | None = None,
) -> Path:
    """Build a cleaned CSV path without targeting the raw source file."""

    output_path = output_directory or PROJECT_ROOT / "data" / "cleaned"
    source_path = config.get("dataset", {}).get("path")
    if source_path is None:
        source_path = config.get("pipeline", {}).get("csv", {}).get("file_path")

    if source_path:
        source_name = Path(source_path).stem
        filename = f"{source_name}_cleaned.csv"
    else:
        filename = "dataset_cleaned.csv"

    return output_path / filename


def save_healed_dataframe(dataframe: pd.DataFrame, output_path: Path) -> str:
    """Persist the healed DataFrame as CSV and return the saved path."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    dataframe.to_csv(output_path, index=False)
    return str(output_path)


def count_validation_statuses(validation_results: list[object]) -> tuple[int, int]:
    """Return passed and failed validation counts."""

    passed = sum(
        1 for result in validation_results if bool(getattr(result, "status", False))
    )
    return passed, len(validation_results) - passed


def main() -> None:
    try:
        config = load_runtime_config()

        ingestion_manager = IngestionManager(config)
        data = ingestion_manager.ingest()
        profiler = DatasetProfiler()
        profiling_manager = ProfilingManager(profiler=profiler)

        validator_factory = ValidatorFactory(config["validation"])
        validators = validator_factory.build()
        validator_manager = ValidatorManager(validators=validators)

        healer_factory = HealerFactory(
            healing_config=config["healing"],
            validation_config=config["validation"],
        )
        healer_manager = HealerManager(healer_factory.build())

        pipeline = Pipeline(
            profiling_manager=profiling_manager,
            validation_manager=validator_manager,
            healer_manager=healer_manager,
            config=config,
        )
        pipeline_result = pipeline.run(data)

        generator = ReportGenerator()
        manager = ReportManager(generator)
        report = manager.generate_report(pipeline_result)
        saved_path = manager.save(report)
        cleaned_dataset_path = save_healed_dataframe(
            pipeline_result.healed_dataframe,
            build_cleaned_dataset_path(config),
        )

        profile_result = pipeline_result.initial_profile
        validation_results = pipeline_result.final_validation
        healing_results = pipeline_result.healing_results
        passed, failed = count_validation_statuses(validation_results)

        print("========================================")
        print("SMART DATA QUALITY PIPELINE COMPLETED")
        print("========================================")
        print()
        print(f"Rows Processed : {getattr(profile_result, 'row_count', 0)}")
        print(f"Validators Run : {len(validation_results)}")
        print(f"Validators OK  : {passed}")
        print(f"Validators Fail: {failed}")
        print(f"Healers Run    : {len(healing_results)}")
        print()
        print("Cleaned Dataset:")
        print()
        print(cleaned_dataset_path)
        print()
        print("Report:")
        print()
        print(saved_path)
    except Exception as exc:
        print(f"Pipeline execution failed: {exc}")
        raise


if __name__ == "__main__":
    main()
