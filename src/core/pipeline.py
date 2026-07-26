from core.pipeline_result import PipelineResult

class Pipeline:
    def __init__(self, profiling_manager, validation_manager):
        self.profiling_manager = profiling_manager
        self.validation_manager = validation_manager
    def run(self, dataframe):
        profile_result = self.profiling_manager.run_profiling(dataframe)
        validation_results = self.validation_manager.run_validations(dataframe)
        return PipelineResult(profile_result=profile_result, validation_results=validation_results)