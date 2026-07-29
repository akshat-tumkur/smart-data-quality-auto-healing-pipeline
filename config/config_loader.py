"""Reusable YAML configuration loading and normalization."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


class ConfigurationError(ValueError):
    """Raised when required configuration is missing or invalid."""


class ConfigLoader:
    """Load and normalize framework configuration from YAML files."""

    def __init__(self, config_directory: str | Path | None = None) -> None:
        self.project_root = Path(__file__).resolve().parents[1]
        self.config_directory = (
            Path(config_directory)
            if config_directory is not None
            else self._default_config_directory()
        )

    def load(self) -> dict[str, Any]:
        """Load all application configuration once."""

        pipeline = self._normalize_pipeline(
            self._load_yaml("pipeline_config.yaml", required=True)
        )
        validation = self._normalize_validation(
            self._load_yaml("validation_rules.yaml", required=True)
        )
        healing = self._normalize_healing(
            self._load_yaml("healing_rules.yaml", required=False)
        )

        return {
            "pipeline": pipeline,
            "dataset": pipeline["dataset"],
            "validation": validation,
            "healing": healing,
            # Backward-compatible keys used by earlier code.
            "validation_rules": validation,
        }

    def _default_config_directory(self) -> Path:
        return self.project_root / "config"

    def _load_yaml(self, filename: str, *, required: bool) -> dict[str, Any]:
        path = self.config_directory / filename
        if not path.exists():
            if required:
                raise ConfigurationError(f"Missing configuration file: {path}")
            return {}

        with path.open("r", encoding="utf-8") as file:
            loaded = yaml.safe_load(file) or {}

        if not isinstance(loaded, dict):
            raise ConfigurationError(f"Configuration file must contain a mapping: {path}")

        return loaded

    def _normalize_pipeline(self, raw_config: dict[str, Any]) -> dict[str, Any]:
        pipeline = dict(raw_config.get("pipeline", raw_config))
        dataset = dict(raw_config.get("dataset", pipeline.get("dataset", {})))

        legacy_csv = pipeline.get("csv", {})
        if "path" not in dataset and legacy_csv.get("file_path"):
            dataset["path"] = legacy_csv["file_path"]

        dataset.setdefault("delimiter", ",")
        dataset.setdefault("encoding", "utf-8")
        dataset.setdefault("has_header", True)

        if not dataset.get("path"):
            raise ConfigurationError("Missing required dataset.path configuration.")

        pipeline.setdefault("name", "smart-data-quality-auto-healing-pipeline")
        pipeline.setdefault("environment", "development")
        pipeline.setdefault("source", "csv")
        pipeline["dataset"] = dataset
        pipeline.setdefault("csv", {})
        pipeline["csv"]["file_path"] = dataset["path"]

        if pipeline["source"] != "csv":
            raise ConfigurationError("Only CSV datasets are currently supported.")

        return pipeline

    def _normalize_validation(self, raw_config: dict[str, Any]) -> dict[str, Any]:
        validation = dict(
            raw_config.get(
                "validation",
                raw_config.get("validation_rules", raw_config),
            )
        )
        if None in validation and "null" not in validation:
            validation["null"] = validation.pop(None)

        validation.setdefault("null", {"enabled": False})
        validation.setdefault("duplicate", {"enabled": False})
        validation.setdefault("regex", [])
        validation.setdefault("datatype", {"enabled": False, "columns": {}})

        datatype = validation.get("datatype", {})
        if isinstance(datatype, list):
            validation["datatype"] = {
                "enabled": bool(datatype),
                "columns": {
                    rule["column"]: rule["type"]
                    for rule in datatype
                    if rule.get("column") and rule.get("type")
                },
            }

        return validation

    def _normalize_healing(self, raw_config: dict[str, Any]) -> dict[str, Any]:
        healing = dict(raw_config.get("healing", raw_config))
        healing.setdefault("missing", {"enabled": False, "strategy": "mean"})
        healing.setdefault("duplicate", {"enabled": False})
        healing.setdefault("datatype", {"enabled": False})
        healing.setdefault("regex", {"enabled": False})
        return healing


def load_config(file_path: str) -> dict[str, Any]:
    """Load one YAML file for backward-compatible callers."""

    path = Path(file_path)
    with path.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}


def load_application_config(
    config_directory: str | Path | None = None,
) -> dict[str, Any]:
    """Load normalized pipeline, validation, and healing configuration."""

    return ConfigLoader(config_directory).load()
