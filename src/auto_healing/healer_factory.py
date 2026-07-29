"""Factory for building auto-healing plugins from YAML configuration."""

from __future__ import annotations

from typing import Any

from auto_healing.base_healer import BaseHealer
from auto_healing.healers.datatype_healer import DatatypeHealer
from auto_healing.healers.duplicate_healer import DuplicateHealer
from auto_healing.healers.missing_value_healer import MissingValueHealer
from auto_healing.healers.regex_healer import RegexHealer


class HealerFactory:
    """Instantiate enabled healer plugins from configuration."""

    def __init__(
        self,
        healing_config: dict[str, Any],
        validation_config: dict[str, Any] | None = None,
    ) -> None:
        self.healing_config = healing_config
        self.validation_config = validation_config or {}

    def build(self) -> list[BaseHealer]:
        """Return configured healer instances in execution order."""

        healers: list[BaseHealer] = []
        healers.extend(self._build_missing_healers())
        healers.extend(self._build_duplicate_healers())
        healers.extend(self._build_datatype_healers())
        healers.extend(self._build_regex_healers())
        return healers

    def _build_missing_healers(self) -> list[BaseHealer]:
        missing_config = self.healing_config.get("missing", {})
        if not missing_config.get("enabled", False):
            return []

        return [
            MissingValueHealer(
                strategy=missing_config.get("strategy", "mean"),
                fill_value=missing_config.get("fill_value"),
                columns=missing_config.get("columns"),
            )
        ]

    def _build_duplicate_healers(self) -> list[BaseHealer]:
        duplicate_config = self.healing_config.get("duplicate", {})
        if not duplicate_config.get("enabled", False):
            return []
        return [DuplicateHealer(subset=duplicate_config.get("subset"))]

    def _build_datatype_healers(self) -> list[BaseHealer]:
        datatype_config = self.healing_config.get("datatype", {})
        if not datatype_config.get("enabled", False):
            return []

        column_types = datatype_config.get("columns")
        if column_types is None:
            column_types = self._validation_datatype_columns()

        return [DatatypeHealer(column_types=column_types)]

    def _build_regex_healers(self) -> list[BaseHealer]:
        regex_config = self.healing_config.get("regex", {})
        if not regex_config.get("enabled", False):
            return []

        return [
            RegexHealer(
                columns=regex_config.get("columns"),
                lowercase_email=regex_config.get("lowercase_email", True),
                trim_whitespace=regex_config.get("trim_whitespace", True),
                remove_phone_symbols=regex_config.get("remove_phone_symbols", True),
            )
        ]

    def _validation_datatype_columns(self) -> dict[str, str]:
        datatype_config = self.validation_config.get("datatype", {})
        if isinstance(datatype_config, list):
            return {
                rule["column"]: rule["type"]
                for rule in datatype_config
                if rule.get("column") and rule.get("type")
            }
        return dict(datatype_config.get("columns", {}))
