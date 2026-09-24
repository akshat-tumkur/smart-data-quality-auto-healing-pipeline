"""Auto-healing orchestration entry point."""

from __future__ import annotations

from time import perf_counter
from typing import Any, Iterable

import pandas as pd

from auto_healing.base_healer import BaseHealer
from auto_healing.healing_result import HealingResult


class HealerManager:
	"""Register and execute auto-healing plugins sequentially."""

	def __init__(self, healers: Iterable[BaseHealer] | None = None) -> None:
		"""Initialize the manager with an optional iterable of healers."""

		self._healers: list[BaseHealer] = list(healers or [])

	def register_healer(self, healer: BaseHealer) -> None:
		"""Register a single healer plugin."""

		self._healers.append(healer)

	def register_healers(self, healers: Iterable[BaseHealer]) -> None:
		"""Register multiple healer plugins."""

		self._healers.extend(healers)

	def heal(
		self,
		dataframe: pd.DataFrame,
		validation_results: Iterable[Any] | None = None,
	) -> tuple[pd.DataFrame, list[HealingResult]]:
		"""Run compatible healers sequentially against a DataFrame.

		When validation results are supplied, only healers matching failed
		validation types are executed. Omitting them preserves legacy behavior.
		"""

		current_dataframe = dataframe.copy(deep=True)
		results: list[HealingResult] = []
		selected_healers = self._select_healers(validation_results)

		for healer in selected_healers:
			start_time = perf_counter()

			try:
				updated_dataframe, result = healer.heal(current_dataframe)
				if not isinstance(updated_dataframe, pd.DataFrame):
					raise TypeError("Healer must return a pandas DataFrame.")
				if not isinstance(result, HealingResult):
					raise TypeError("Healer must return a HealingResult instance.")

				if result.status == "success":
					current_dataframe = updated_dataframe
				results.append(result)
			except Exception as exc:
				results.append(
					HealingResult(
						healer_name=healer.healer_name,
						status="failed",
						message="Healer execution failed.",
						rows_affected=0,
						execution_time=perf_counter() - start_time,
						metadata={
							"exception_type": type(exc).__name__,
							"exception_message": str(exc),
						},
					)
				)

		return current_dataframe, results

	def _select_healers(
		self,
		validation_results: Iterable[Any] | None,
	) -> list[BaseHealer]:
		if validation_results is None:
			return list(self._healers)

		failed_types = {
			self._validation_type(result)
			for result in validation_results
			if not bool(getattr(result, "status", False))
		}
		return [
			healer
			for healer in self._healers
			if failed_types.intersection(getattr(healer, "validation_types", frozenset()))
		]

	@staticmethod
	def _validation_type(result: Any) -> str:
		validation_type = getattr(result, "validation_type", None)
		if validation_type:
			return str(validation_type)

		metadata = getattr(result, "metadata", {}) or {}
		if metadata.get("validation_type"):
			return str(metadata["validation_type"])

		name = str(getattr(result, "validator_name", "")).lower()
		for token in ("missing", "null", "duplicate", "datatype", "data type", "regex"):
			if token in name:
				return "missing" if token == "null" else token.replace(" ", "")
		return "unknown"
