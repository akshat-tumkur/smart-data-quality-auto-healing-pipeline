"""Base abstractions for auto-healing plugins."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import pandas as pd

from auto_healing.healing_result import HealingResult


class BaseHealer(ABC):
	"""Abstract base class for DataFrame healers."""

	display_name: str | None = None

	@property
	def healer_name(self) -> str:
		"""Return the human-readable healer name."""

		return self.display_name or self.__class__.__name__

	@abstractmethod
	def heal(self, dataframe: pd.DataFrame) -> tuple[pd.DataFrame, HealingResult]:
		"""Heal the supplied DataFrame and return the updated frame and result."""

	def build_result(
		self,
		*,
		status: str,
		message: str,
		rows_affected: int,
		execution_time: float,
		metadata: dict[str, Any] | None = None,
	) -> HealingResult:
		"""Create a standardized healing result."""

		return HealingResult(
			healer_name=self.healer_name,
			status=status,
			message=message,
			rows_affected=rows_affected,
			execution_time=execution_time,
			metadata=metadata or {},
		)