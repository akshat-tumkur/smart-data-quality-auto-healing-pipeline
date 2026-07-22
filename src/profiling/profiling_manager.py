"""Manager wrapper for dataset profiling."""

from __future__ import annotations
from typing import Any
import pandas as pd



class ProfilingManager:
    """Coordinate a profiler instance for a DataFrame."""

    def __init__(self, profiler: Any) -> None:
        self.profiler = profiler

    def run_profiling(self, dataframe: pd.DataFrame):
        """Run profiling and return the generated profile result."""
        return self.profiler.profile(dataframe)
