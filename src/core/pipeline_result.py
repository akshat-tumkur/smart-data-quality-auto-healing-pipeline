"""Result container for complete pipeline execution."""

from __future__ import annotations

import pandas as pd

from profiling.profile_result import ProfileResult


class PipelineResult:
    def __init__(
        self,
        dataframe: pd.DataFrame,
        initial_schema_result: object | None = None,
        initial_profile: ProfileResult | None = None,
        initial_validation: list[object] | None = None,
        healed_dataframe: pd.DataFrame | None = None,
        healing_results: list[object] | None = None,
        final_profile: ProfileResult | None = None,
        final_validation: list[object] | None = None,
        profile_result: ProfileResult | None = None,
        validation_results: list[object] | None = None,
    ) -> None:
        self.dataframe = dataframe
        self.initial_schema_result = initial_schema_result
        self.initial_profile = (
            initial_profile if initial_profile is not None else profile_result
        )
        self.initial_validation = (
            initial_validation
            if initial_validation is not None
            else validation_results or []
        )
        self.healed_dataframe = (
            healed_dataframe if healed_dataframe is not None else dataframe
        )
        self.healing_results = healing_results or []
        self.final_profile = (
            final_profile if final_profile is not None else self.initial_profile
        )
        self.final_validation = (
            final_validation if final_validation is not None else self.initial_validation
        )

        # Backwards-compatible aliases for existing callers.
        self.profile_result = self.initial_profile
        self.validation_results = self.initial_validation
        self.schema_result = self.initial_schema_result

    def __repr__(self) -> str:
        return (
            "PipelineResult("
            f"initial_schema_result={self.initial_schema_result}, "
            f"initial_profile={self.initial_profile}, "
            f"initial_validation={self.initial_validation}, "
            f"healing_results={self.healing_results}, "
            f"final_profile={self.final_profile}, "
            f"final_validation={self.final_validation})"
        )
