from time import perf_counter
from dataclasses import replace
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
        healing_results = self._reconcile_healing_results(
            healing_results,
            initial_validation,
            final_validation,
        )
        initial_quality = self.quality_calculator.calculate(
            initial_profile,
            initial_validation,
        )
        final_quality = self.quality_calculator.calculate(
            final_profile,
            final_validation,
        )
        quality_score = self.quality_calculator.compare(initial_quality, final_quality)
        metrics = self._build_metrics(
            initial_profile,
            final_profile,
            initial_validation,
            final_validation,
        )
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
    def _build_metrics(
        initial_profile: Any,
        final_profile: Any,
        initial_validation: list[Any] | None = None,
        final_validation: list[Any] | None = None,
    ) -> dict[str, Any]:
        metrics = {}
        for name, attribute in (
            ("missing_values", "total_missing_values"),
            ("duplicates", "duplicate_rows"),
            ("rows", "row_count"),
        ):
            before = int(getattr(initial_profile, attribute, 0))
            after = int(getattr(final_profile, attribute, 0))
            metrics[name] = {"before": before, "after": after, "delta": after - before}

        initial_duplicate = next(
            (
                result
                for result in (initial_validation or [])
                if "duplicate" in str(getattr(result, "validator_name", "")).lower()
            ),
            None,
        )
        final_duplicate = next(
            (
                result
                for result in (final_validation or [])
                if "duplicate" in str(getattr(result, "validator_name", "")).lower()
            ),
            None,
        )
        initial_duplicate_rows = int(getattr(initial_duplicate, "rows_affected", 0))
        final_duplicate_rows = int(getattr(final_duplicate, "rows_affected", 0))
        metrics["duplicate_affected_rows"] = {
            "before": initial_duplicate_rows,
            "after": final_duplicate_rows,
            "delta": final_duplicate_rows - initial_duplicate_rows,
        }
        initial_duplicate_groups = int(
            (getattr(initial_duplicate, "metadata", {}) or {}).get("duplicate_groups", 0)
        )
        final_duplicate_groups = int(
            (getattr(final_duplicate, "metadata", {}) or {}).get("duplicate_groups", 0)
        )
        metrics["duplicate_groups"] = {
            "before": initial_duplicate_groups,
            "after": final_duplicate_groups,
            "delta": final_duplicate_groups - initial_duplicate_groups,
        }
        return metrics

    @staticmethod
    def _reconcile_healing_results(
        healing_results: list[Any],
        initial_validation: list[Any],
        final_validation: list[Any],
    ) -> list[Any]:
        """Make healer status and repair counts reflect final validation."""

        reconciled = []
        for result in healing_results:
            operation = str(getattr(result, "healer_name", "")).lower()
            validation_type = next(
                (
                    token
                    for token, marker in (
                        ("missing", "missing"),
                        ("duplicate", "duplicate"),
                        ("datatype", "datatype"),
                        ("regex", "regex"),
                    )
                    if marker in operation
                ),
                None,
            )
            if validation_type is None:
                reconciled.append(result)
                continue

            initial_count = Pipeline._validation_count(initial_validation, validation_type)
            remaining_count = Pipeline._validation_count(final_validation, validation_type)
            repaired_count = max(initial_count - remaining_count, 0)
            metadata = dict(getattr(result, "metadata", {}) or {})
            metadata.update(
                {
                    "initial_affected": initial_count,
                    "repaired": repaired_count,
                    "remaining": remaining_count,
                    "attempted": initial_count,
                    "changed": repaired_count,
                    "unresolved": remaining_count,
                }
            )

            if initial_count == 0 or remaining_count == 0:
                status = "success"
            elif repaired_count > 0:
                status = "partial"
            else:
                status = "failed"
            message = (
                f"{getattr(result, 'healer_name', 'Healer')} reconciliation: "
                f"initial affected={initial_count}, repaired={repaired_count}, "
                f"remaining={remaining_count}."
            )
            reconciled.append(
                replace(
                    result,
                    status=status,
                    message=message,
                    metadata=metadata,
                )
            )
        return reconciled

    @staticmethod
    def _validation_count(results: list[Any], validation_type: str) -> int:
        counts = []
        for result in results:
            name = str(getattr(result, "validator_name", "")).lower()
            if (
                (validation_type == "missing" and "null" in name)
                or (validation_type == "duplicate" and "duplicate" in name)
                or (validation_type == "datatype" and "data type" in name)
                or (validation_type == "regex" and "regex" in name)
            ):
                counts.append(int(getattr(result, "rows_affected", 0)))
        return sum(counts)
