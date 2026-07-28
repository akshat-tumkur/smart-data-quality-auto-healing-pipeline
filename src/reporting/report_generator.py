"""Text report generation for pipeline execution results."""

from __future__ import annotations

from typing import Any, Iterable


class ReportGenerator:
    """Generate a formatted text report from a pipeline result."""

    def generate(self, pipeline_result: Any) -> str:
        """Return a human-readable report for the supplied pipeline result."""

        profile_result = self._get_profile_result(pipeline_result)
        healing_results = self._get_healing_results(pipeline_result)
        validation_results = self._get_validation_results(pipeline_result)

        sections = [
            self._render_title(),
            self._render_dataset_summary(profile_result),
            self._render_healing_results(healing_results),
            self._render_validation_results(validation_results),
            self._render_summary(validation_results),
        ]
        return "\n\n".join(section for section in sections if section)

    def _render_title(self) -> str:
        return "\n".join(
            [
                "====================================================",
                "SMART DATA QUALITY REPORT",
                "====================================================",
            ]
        )

    def _render_dataset_summary(self, profile_result: Any) -> str:
        lines = ["DATASET SUMMARY", ""]
        lines.extend(
            [
                self._format_metric("Rows", self._get_value(profile_result, "row_count", 0)),
                self._format_metric(
                    "Columns", self._get_value(profile_result, "column_count", 0)
                ),
                self._format_metric(
                    "Duplicate Rows", self._get_value(profile_result, "duplicate_rows", 0)
                ),
                self._format_metric(
                    "Missing Values",
                    self._get_value(profile_result, "total_missing_values", 0),
                ),
                self._format_metric(
                    "Memory Usage", self._get_value(profile_result, "memory_usage", 0)
                ),
            ]
        )
        return "\n".join(lines)

    def _render_healing_results(self, healing_results: Iterable[Any]) -> str:
        lines = [
            "----------------------------------------------------",
            "AUTO-HEALING RESULTS",
            "----------------------------------------------------",
            "",
        ]

        results = list(healing_results)
        if not results:
            lines.append("No healing results available.")
            lines.append("")
            return "\n".join(lines)

        successful = sum(1 for result in results if self._get_value(result, "status", "") == "success")
        failed = len(results) - successful
        lines.extend(
            [
                self._format_metric("Healers Run", len(results)),
                self._format_metric("Succeeded", successful),
                self._format_metric("Failed", failed),
                "",
            ]
        )

        for index, healing_result in enumerate(results):
            lines.extend(self._render_healing_result(healing_result))
            if index < len(results) - 1:
                lines.append("----------------------------------------------------")
                lines.append("")

        return "\n".join(lines)

    def _render_healing_result(self, healing_result: Any) -> list[str]:
        healer_name = self._get_value(healing_result, "healer_name", "Healer")
        status = self._get_value(healing_result, "status", "failed")
        rows_affected = self._get_value(healing_result, "rows_affected", 0)
        message = self._get_value(healing_result, "message", "")

        status_label = str(status).upper()
        status_icon = "✅" if status == "success" else "❌"

        return [
            f"{status_icon} {healer_name}",
            "",
            self._format_metric("Status", status_label),
            self._format_metric("Affected Rows", rows_affected),
            "",
            self._format_metric("Message", message or "No message provided."),
        ]

    def _render_validation_results(self, validation_results: Iterable[Any]) -> str:
        lines = [
            "----------------------------------------------------",
            "VALIDATION RESULTS",
            "----------------------------------------------------",
            "",
        ]

        results = list(validation_results)
        if not results:
            lines.append("No validation results available.")
            lines.append("")
            return "\n".join(lines)

        for index, validation_result in enumerate(results):
            lines.extend(self._render_validation_result(validation_result))
            if index < len(results) - 1:
                lines.append("----------------------------------------------------")
                lines.append("")

        return "\n".join(lines)

    def _render_validation_result(self, validation_result: Any) -> list[str]:
        validator_name = self._get_value(validation_result, "validator_name", "Validator")
        status = self._get_value(validation_result, "status", False)
        rows_affected = self._get_value(validation_result, "rows_affected", 0)
        message = self._get_value(validation_result, "message", "")

        status_label = "PASSED" if bool(status) else "FAILED"
        status_icon = "✅" if bool(status) else "❌"

        return [
            f"{status_icon} {validator_name}",
            "",
            self._format_metric("Status", status_label),
            self._format_metric("Affected Rows", rows_affected),
            "",
            self._format_metric("Message", message or "No message provided."),
        ]

    def _render_summary(self, validation_results: Iterable[Any]) -> str:
        results = list(validation_results)
        passed = sum(1 for result in results if bool(self._get_value(result, "status", False)))
        failed = len(results) - passed

        return "\n".join(
            [
                "====================================================",
                "SUMMARY",
                "",
                self._format_metric("Total Validators", len(results)),
                self._format_metric("Passed", passed),
                self._format_metric("Failed", failed),
                "",
                "====================================================",
            ]
        )

    def _format_metric(self, label: str, value: Any) -> str:
        return f"{label:<20}: {value}"

    def _get_profile_result(self, pipeline_result: Any) -> Any:
        return self._get_value(pipeline_result, "profile_result", None)

    def _get_validation_results(self, pipeline_result: Any) -> list[Any]:
        results = self._get_value(pipeline_result, "validation_results", [])
        if results is None:
            return []
        return list(results)

    def _get_healing_results(self, pipeline_result: Any) -> list[Any]:
        results = self._get_value(pipeline_result, "healing_results", [])
        if results is None:
            return []
        return list(results)

    def _get_value(self, container: Any, attribute: str, default: Any) -> Any:
        if container is None:
            return default
        return getattr(container, attribute, default)