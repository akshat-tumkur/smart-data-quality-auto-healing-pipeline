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

        raw_pipeline = self._load_yaml("pipeline_config.yaml", required=True)
        pipeline = self._normalize_pipeline(raw_pipeline)
        validation = self._normalize_validation(
            self._load_yaml("validation_rules.yaml", required=True)
        )
        healing = self._normalize_healing(
            self._load_yaml("healing_rules.yaml", required=False)
        )
        schema = self._normalize_schema(raw_pipeline)
        anomaly_detection = self._normalize_anomaly_detection(raw_pipeline)
        quality_score = self._normalize_quality_score(raw_pipeline)

        return {
            "pipeline": pipeline,
            "dataset": pipeline["dataset"],
            "schema": schema,
            "anomaly_detection": anomaly_detection,
            "quality_score": quality_score,
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

    def _normalize_schema(self, raw_config: dict[str, Any]) -> dict[str, Any]:
        schema = dict(raw_config.get("schema", {}))
        schema.setdefault("allow_extra_columns", True)

        columns = schema.get("columns", {})
        if not isinstance(columns, dict):
            raise ConfigurationError("schema.columns must be a mapping of column definitions.")

        normalized_columns: dict[str, Any] = {}
        for column_name, definition in columns.items():
            if not isinstance(definition, dict):
                raise ConfigurationError(
                    f"schema.columns.{column_name} must be a mapping with type and nullable fields."
                )

            column_type = definition.get("type")
            if column_type is None:
                raise ConfigurationError(f"schema.columns.{column_name}.type is required.")

            nullable = definition.get("nullable", True)
            normalized_columns[column_name] = {
                "type": str(column_type),
                "nullable": bool(nullable),
            }

        schema["columns"] = normalized_columns
        return schema

    def _normalize_anomaly_detection(self, raw_config: dict[str, Any]) -> dict[str, Any]:
        anomaly_detection = dict(raw_config.get("anomaly_detection", {}))
        anomaly_detection.setdefault("enabled", False)
        anomaly_detection.setdefault("method", "isolation_forest")
        anomaly_detection.setdefault("contamination", 0.05)
        anomaly_detection.setdefault("random_state", 42)

        contamination = float(anomaly_detection["contamination"])
        if not 0 < contamination <= 0.5:
            raise ConfigurationError(
                "anomaly_detection.contamination must be greater than 0 and at most 0.5."
            )
        anomaly_detection["contamination"] = contamination
        anomaly_detection["random_state"] = int(anomaly_detection["random_state"])
        if anomaly_detection["method"] != "isolation_forest":
            raise ConfigurationError(
                "Only anomaly_detection.method=isolation_forest is currently supported."
            )
        return anomaly_detection

    def _normalize_quality_score(self, raw_config: dict[str, Any]) -> dict[str, Any]:
        quality_score = dict(raw_config.get("quality_score", {}))
        quality_score.setdefault("enabled", False)
        weights = quality_score.get("weights", {})
        if not isinstance(weights, dict):
            raise ConfigurationError("quality_score.weights must be a mapping.")
        quality_score["weights"] = {
            name: float(value)
            for name, value in weights.items()
        }
        return quality_score


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
