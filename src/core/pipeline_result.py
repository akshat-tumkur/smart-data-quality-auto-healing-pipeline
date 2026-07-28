from profiling.profile_result import ProfileResult

class PipelineResult:
    def __init__(
        self,
        dataframe,
        profile_result: ProfileResult,
        validation_results: list,
        healed_dataframe=None,
        healing_results: list | None = None,
    ):
        self.dataframe = dataframe
        self.profile_result = profile_result
        self.validation_results = validation_results
        self.healed_dataframe = healed_dataframe if healed_dataframe is not None else dataframe
        self.healing_results = healing_results or []

    def __repr__(self):
        return (
            "PipelineResult("
            f"profile_result={self.profile_result}, "
            f"validation_results={self.validation_results}, "
            f"healing_results={self.healing_results})"
        )