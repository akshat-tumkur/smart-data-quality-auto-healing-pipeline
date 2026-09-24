from time import perf_counter
from typing import Any

import pandas as pd

from anomaly_detection import AnomalyDetectorFactory
from audit import AuditTrailBuilder
from core.pipeline_result import PipelineResult
from quality import QualityScoreCalculator


class Pipeline:
    def __init__(
        self,
        profiling_manager: Any,
        validation_manager: Any,
        healer_manager: Any,
        schema_manager: Any,
        config: dict[str, Any] | None = None,
        anomaly_detector: Any = None,
        quality_calculator: Any = None,
        audit_trail_builder: Any = None,
    ) -> None:
        self.profiling_manager = profiling_manager
        self.validation_manager = validation_manager
        self.healer_manager = healer_manager
        self.schema_manager = schema_manager
        self.config = config or {}
        self.anomaly_detector = (
            anomaly_detector
            if anomaly_detector is not None
            else AnomalyDetectorFactory().build(self.config.get("anomaly_detection", {}))
        )
        self.quality_calculator = (
            quality_calculator
            if quality_calculator is not None
            else QualityScoreCalculator(self.config.get("quality_score", {}))
        )
        self.audit_trail_builder = audit_trail_builder or AuditTrailBuilder()

    def run(self, dataframe: pd.DataFrame) -> PipelineResult:
        start_time = perf_counter()
        schema_result = self.schema_manager.run_schema_validation(
            dataframe,
            self.config.get("schema", {}),
        )

        if schema_result.missing_columns:
            result = PipelineResult(
                dataframe=dataframe,
                initial_schema_result=schema_result,
            )
            result.audit_trail = self.audit_trail_builder.build(
                config=self.config,
                schema_result=schema_result,
                initial_validation=[],
                anomaly_result=None,
                healing_results=[],
                final_validation=[],
                metrics={},
                quality_score={"enabled": False},
                execution_time=perf_counter() - start_time,
            )
            result.execution_time = perf_counter() - start_time
            return result

        initial_profile = self.profiling_manager.run_profiling(dataframe)
        initial_validation = self.validation_manager.run_validations(dataframe)
        anomaly_result = None
        if self.anomaly_detector is not None:
            anomaly_result = self.anomaly_detector.detect(dataframe)
        healed_dataframe = dataframe
        healing_results = []

        if self.healer_manager is not None:
            try:
                healed_dataframe, healing_results = self.healer_manager.heal(
                    dataframe,
                    validation_results=initial_validation,
                )
            except TypeError as exc:
                if "validation_results" not in str(exc):
                    raise
                healed_dataframe, healing_results = self.healer_manager.heal(dataframe)

        final_profile = self.profiling_manager.run_profiling(healed_dataframe)
        final_validation = self.validation_manager.run_validations(healed_dataframe)
        initial_quality = self.quality_calculator.calculate(
            initial_profile,
            initial_validation,
        )
        final_quality = self.quality_calculator.calculate(
            final_profile,
            final_validation,
        )
        quality_score = self.quality_calculator.compare(initial_quality, final_quality)
        metrics = self._build_metrics(initial_profile, final_profile)
        result = PipelineResult(
            dataframe=dataframe,
            initial_schema_result=schema_result,
            initial_profile=initial_profile,
            initial_validation=initial_validation,
            anomaly_detection_result=anomaly_result,
            healed_dataframe=healed_dataframe,
            healing_results=healing_results,
            final_profile=final_profile,
            final_validation=final_validation,
            initial_quality_score=initial_quality,
            final_quality_score=final_quality,
            quality_score=quality_score,
            metrics=metrics,
        )
        result.audit_trail = self.audit_trail_builder.build(
            config=self.config,
            schema_result=schema_result,
            initial_validation=initial_validation,
            anomaly_result=anomaly_result,
            healing_results=healing_results,
            final_validation=final_validation,
            metrics=metrics,
            quality_score=quality_score,
            execution_time=perf_counter() - start_time,
        )
        result.execution_time = perf_counter() - start_time
        return result

    @staticmethod
    def _build_metrics(initial_profile: Any, final_profile: Any) -> dict[str, Any]:
        metrics = {}
        for name, attribute in (
            ("missing_values", "total_missing_values"),
            ("duplicates", "duplicate_rows"),
            ("rows", "row_count"),
        ):
            before = int(getattr(initial_profile, attribute, 0))
            after = int(getattr(final_profile, attribute, 0))
            metrics[name] = {"before": before, "after": after, "delta": after - before}
        return metrics
