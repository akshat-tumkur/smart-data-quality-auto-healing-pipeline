from typing import Any

import pandas as pd

from core.pipeline_result import PipelineResult


class Pipeline:
    def __init__(
        self,
        profiling_manager: Any,
        validation_manager: Any,
        healer_manager: Any,
        config: dict[str, Any] | None = None,
    ) -> None:
        self.profiling_manager = profiling_manager
        self.validation_manager = validation_manager
        self.healer_manager = healer_manager
        self.config = config or {}

    def run(self, dataframe: pd.DataFrame) -> PipelineResult:
        initial_profile = self.profiling_manager.run_profiling(dataframe)
        initial_validation = self.validation_manager.run_validations(dataframe)
        healed_dataframe = dataframe
        healing_results = []

        if self.healer_manager is not None:
            healed_dataframe, healing_results = self.healer_manager.heal(dataframe)

        final_profile = self.profiling_manager.run_profiling(healed_dataframe)
        final_validation = self.validation_manager.run_validations(healed_dataframe)

        return PipelineResult(
            dataframe=dataframe,
            initial_profile=initial_profile,
            initial_validation=initial_validation,
            healed_dataframe=healed_dataframe,
            healing_results=healing_results,
            final_profile=final_profile,
            final_validation=final_validation,
        )
