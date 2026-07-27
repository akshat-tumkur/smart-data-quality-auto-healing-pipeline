from profiling.profile_result import ProfileResult

class PipelineResult:
    def __init__(self, dataframe, profile_result: ProfileResult, validation_results: list):
        self.dataframe = dataframe
        self.profile_result = profile_result
        self.validation_results = validation_results
    def __repr__(self):
            return f"PipelineResult(profile_result={self.profile_result}, validation_results={self.validation_results}))"