from core.pipeline_result import PipelineResult


class Pipeline:
    def __init__(self, profiling_manager, validation_manager, healer_manager):
        self.profiling_manager = profiling_manager
        self.validation_manager = validation_manager
        self.healer_manager = healer_manager

    def run(self, dataframe):
        profile_result = self.profiling_manager.run_profiling(dataframe)
        validation_results = self.validation_manager.run_validations(dataframe)
        healed_dataframe = dataframe
        healing_results = []

        if self.healer_manager is not None:
            healed_dataframe, healing_results = self.healer_manager.heal(dataframe)

        return PipelineResult(
            dataframe=dataframe,
            profile_result=profile_result,
            validation_results=validation_results,
            healed_dataframe=healed_dataframe,
            healing_results=healing_results,
        )