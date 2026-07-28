"""Serializable result model for auto-healing operations."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class HealingResult:
	"""Capture the outcome of a single healing plugin execution."""

	healer_name: str
	status: str
	message: str = ""
	rows_affected: int = 0
	execution_time: float = 0.0
	metadata: dict[str, Any] = field(default_factory=dict)

	def to_dict(self) -> dict[str, Any]:
		"""Return a JSON-serializable representation of the result."""

		return {
			"healer_name": self.healer_name,
			"status": self.status,
			"message": self.message,
			"rows_affected": self.rows_affected,
			"execution_time": self.execution_time,
			"metadata": dict(self.metadata),
		}