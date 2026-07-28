"""Duplicate row healing plugin."""

from __future__ import annotations

from time import perf_counter
from typing import Any, Sequence

import pandas as pd

from auto_healing.base_healer import BaseHealer
from auto_healing.healing_result import HealingResult


class DuplicateHealer(BaseHealer):
    """Remove duplicate rows while preserving the first occurrence."""

    display_name = "Duplicate Healer"

    def __init__(self, subset: Sequence[str] | None = None) -> None:
        """Initialize the healer with an optional duplicate key subset."""

        self.subset = list(subset) if subset is not None else None

    def heal(self, dataframe: pd.DataFrame) -> tuple[pd.DataFrame, HealingResult]:
        """Remove duplicate rows and return the updated DataFrame and result."""

        start_time = perf_counter()

        try:
            working_dataframe = dataframe
            before_count = len(working_dataframe)
            working_dataframe = working_dataframe.drop_duplicates(
                subset=self.subset,
                keep="first",
            )
            removed_count = before_count - len(working_dataframe)
            metadata = {
                "subset": self.subset,
                "kept": "first",
                "removed_rows": removed_count,
            }
            message = (
                f"Removed {removed_count} duplicate rows."
                if removed_count > 0
                else "No duplicate rows were found."
            )
            return (
                working_dataframe,
                self.build_result(
                    status="success",
                    message=message,
                    rows_affected=removed_count,
                    execution_time=perf_counter() - start_time,
                    metadata=metadata,
                ),
            )
        except Exception as exc:
            return (
                    dataframe,
                    self.build_result(
                    status="failed",
                    message="Duplicate healing failed.",
                    rows_affected=0,
                    execution_time=perf_counter() - start_time,
                    metadata={
                        "subset": self.subset,
                        "exception_type": type(exc).__name__,
                        "exception_message": str(exc),
                    },
                ),
            )