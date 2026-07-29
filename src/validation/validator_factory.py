"""Factory for building validators from YAML configuration."""

from __future__ import annotations

from typing import Any

from utils.regex_aliases import resolve_regex_pattern
from validation.base_validator import BaseValidator
from validation.validators.datatype_validator import DataTypeValidator
from validation.validators.duplicate_validator import DuplicateValidator
from validation.validators.null_validator import NullValidator
from validation.validators.regex_validator import RegexValidator


class ValidatorFactory:
    """Instantiate enabled validator plugins from configuration."""

    def __init__(self, validation_config: dict[str, Any]) -> None:
        self.validation_config = validation_config

    def build(self) -> list[BaseValidator]:
        """Return configured validator instances."""

        validators: list[BaseValidator] = []
        validators.extend(self._build_null_validators())
        validators.extend(self._build_duplicate_validators())
        validators.extend(self._build_datatype_validators())
        validators.extend(self._build_regex_validators())
        return validators

    def _build_null_validators(self) -> list[BaseValidator]:
        null_config = self.validation_config.get("null", {})
        if not null_config.get("enabled", False):
            return []
        return [NullValidator()]

    def _build_duplicate_validators(self) -> list[BaseValidator]:
        duplicate_config = self.validation_config.get("duplicate", {})
        if not duplicate_config.get("enabled", False):
            return []
        return [DuplicateValidator(subset=duplicate_config.get("subset"))]

    def _build_datatype_validators(self) -> list[BaseValidator]:
        datatype_config = self.validation_config.get("datatype", {})
        if isinstance(datatype_config, list):
            rules = datatype_config
            enabled = bool(rules)
        else:
            rules = [
                {"column": column, "type": expected_type}
                for column, expected_type in datatype_config.get("columns", {}).items()
            ]
            enabled = datatype_config.get("enabled", False)

        if not enabled:
            return []

        return [
            DataTypeValidator(rule["column"], rule["type"])
            for rule in rules
            if rule.get("column") and rule.get("type")
        ]

    def _build_regex_validators(self) -> list[BaseValidator]:
        regex_config = self.validation_config.get("regex", [])
        if isinstance(regex_config, dict):
            if not regex_config.get("enabled", False):
                return []
            rules = regex_config.get("rules", [])
        else:
            rules = regex_config

        return [
            RegexValidator(rule["column"], resolve_regex_pattern(rule["pattern"]))
            for rule in rules
            if rule.get("column") and rule.get("pattern")
        ]
