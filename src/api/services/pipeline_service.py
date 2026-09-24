"""Application service for running the existing data-quality pipeline."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from uuid import uuid4

import pandas as pd

from auto_healing import HealerManager
from auto_healing.healer_factory import HealerFactory
from config.config_loader import load_application_config
from core.pipeline import Pipeline
from ingestion.csv_loader import CSVLoader
from profiling.dataset_profiler import DatasetProfiler
from profiling.profiling_manager import ProfilingManager
from reporting.report_generator import ReportGenerator
from reporting.report_manager import ReportManager
from schema.schema_manager import SchemaManager
from schema.schema_validator import SchemaValidator
from validation.validator_factory import ValidatorFactory
from validation.validator_manager import ValidatorManager


class PipelineService:
    """Build and run one synchronous pipeline execution for an uploaded CSV."""

    def __init__(
        self,
        project_root: Path | None = None,
        config: dict | None = None,
    ) -> None:
        self.project_root = project_root or Path(__file__).resolve().parents[3]
        self.config = config or load_application_config()

    def run_csv(self, filename: str, content: bytes) -> dict:
        run_id = uuid4().hex
        staging_path = self._save_upload(run_id, filename, content)
        runtime_config = deepcopy(self.config)
        runtime_config["dataset"]["path"] = str(staging_path)
        runtime_config["pipeline"]["dataset"]["path"] = str(staging_path)
        runtime_config["pipeline"]["csv"]["file_path"] = str(staging_path)

        data = CSVLoader().load(
            str(staging_path),
            delimiter=runtime_config["dataset"].get("delimiter", ","),
            encoding=runtime_config["dataset"].get("encoding", "utf-8"),
            has_header=runtime_config["dataset"].get("has_header", True),
        )
        pipeline_result = self._build_pipeline(runtime_config).run(data)

        cleaned_path = self.project_root / "data" / "cleaned" / f"{run_id}_cleaned.csv"
        cleaned_path.parent.mkdir(parents=True, exist_ok=True)
        pipeline_result.healed_dataframe.to_csv(cleaned_path, index=False)

        report_path = ReportManager(ReportGenerator()).save(
            ReportGenerator().generate(pipeline_result)
        )
        payload = pipeline_result.to_dict()
        payload.update(
            {
                "status": "schema_failed" if pipeline_result.initial_schema_result and pipeline_result.initial_schema_result.missing_columns else "success",
                "run_id": run_id,
                "output": {
                    "cleaned_dataset": str(cleaned_path),
                    "report": report_path,
                },
            }
        )
        return payload

    def _build_pipeline(self, config: dict) -> Pipeline:
        validators = ValidatorFactory(config["validation"]).build()
        healer_factory = HealerFactory(
            healing_config=config["healing"],
            validation_config=config["validation"],
        )
        return Pipeline(
            profiling_manager=ProfilingManager(DatasetProfiler()),
            validation_manager=ValidatorManager(validators),
            healer_manager=HealerManager(healer_factory.build()),
            schema_manager=SchemaManager(SchemaValidator()),
            config=config,
        )

    def _save_upload(self, run_id: str, filename: str, content: bytes) -> Path:
        safe_name = Path(filename or "dataset.csv").name
        staging_path = self.project_root / "data" / "staging" / f"{run_id}_{safe_name}"
        staging_path.parent.mkdir(parents=True, exist_ok=True)
        staging_path.write_bytes(content)
        return staging_path