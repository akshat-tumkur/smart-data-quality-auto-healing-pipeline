"""Text report generation for pipeline execution results."""

from __future__ import annotations

from typing import Any, Iterable


class ReportGenerator:
    """Generate a formatted text report from a pipeline result."""

    def generate(self, pipeline_result: Any) -> str:
        """Return a human-readable report for the supplied pipeline result."""

        initial_profile = self._get_initial_profile(pipeline_result)
        initial_validation = self._get_initial_validation(pipeline_result)
        healing_results = self._get_healing_results(pipeline_result)
        final_profile = self._get_final_profile(pipeline_result)
        final_validation = self._get_final_validation(pipeline_result)

        sections = [
            self._render_title(),
            self._render_dataset_section(
                "INITIAL DATASET",
                initial_profile,
                "INITIAL VALIDATION",
                initial_validation,
            ),
            self._render_healing_results(healing_results),
            self._render_dataset_section(
                "FINAL DATASET",
                final_profile,
                "FINAL VALIDATION",
                final_validation,
            ),
            self._render_improvement_summary(
                initial_profile,
                final_profile,
                initial_validation,
                final_validation,
            ),
            self._render_summary(final_validation, healing_results),
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

    def _render_dataset_section(
        self,
        dataset_title: str,
        profile_result: Any,
        validation_title: str,
        validation_results: Iterable[Any],
    ) -> str:
        lines = [
            dataset_title,
            "",
            self._format_metric("Rows", self._get_value(profile_result, "row_count", 0)),
            self._format_metric(
                "Columns",
                self._get_value(profile_result, "column_count", 0),
            ),
            self._format_metric(
                "Duplicate Rows",
                self._get_value(profile_result, "duplicate_rows", 0),
            ),
            self._format_metric(
                "Missing Values",
                self._get_value(profile_result, "total_missing_values", 0),
            ),
            "",
            "---",
            "",
            validation_title,
            "",
        ]
        lines.extend(self._render_validation_items(validation_results))
        return "\n".join(lines)

    def _render_healing_results(self, healing_results: Iterable[Any]) -> str:
        lines = [
            "====================================================",
            "AUTO-HEALING SUMMARY",
            "====================================================",
            "",
        ]

        results = list(healing_results)
        if not results:
            lines.append("No healing results available.")
            lines.append("")
            return "\n".join(lines)

        successful = sum(
            1 for result in results if self._get_value(result, "status", "") == "success"
        )
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
        status_icon = "[OK]" if status == "success" else "[FAILED]"

        return [
            f"{status_icon} {healer_name}",
            "",
            self._format_metric("Status", status_label),
            self._format_metric("Affected Rows", rows_affected),
            "",
            self._format_metric("Message", message or "No message provided."),
        ]

    def _render_validation_items(self, validation_results: Iterable[Any]) -> list[str]:
        results = list(validation_results)
        if not results:
            return ["No validation results available.", ""]

        lines = []
        for index, validation_result in enumerate(results):
            lines.extend(self._render_validation_result(validation_result))
            if index < len(results) - 1:
                lines.append("----------------------------------------------------")
                lines.append("")

        return lines

    def _render_validation_result(self, validation_result: Any) -> list[str]:
        validator_name = self._get_value(validation_result, "validator_name", "Validator")
        status = self._get_value(validation_result, "status", False)
        rows_affected = self._get_value(validation_result, "rows_affected", 0)
        message = self._get_value(validation_result, "message", "")

        status_label = "PASSED" if bool(status) else "FAILED"
        status_icon = "[PASSED]" if bool(status) else "[FAILED]"

        return [
            f"{status_icon} {validator_name}",
            "",
            self._format_metric("Status", status_label),
            self._format_metric("Affected Rows", rows_affected),
            "",
            self._format_metric("Message", message or "No message provided."),
        ]

    def _render_improvement_summary(
        self,
        initial_profile: Any,
        final_profile: Any,
        initial_validation: Iterable[Any],
        final_validation: Iterable[Any],
    ) -> str:
        initial_passed, initial_failed = self._count_validation_statuses(
            initial_validation
        )
        final_passed, final_failed = self._count_validation_statuses(final_validation)

        return "\n".join(
            [
                "====================================================",
                "IMPROVEMENT SUMMARY",
                "====================================================",
                "",
                self._format_transition(
                    "Missing Values",
                    self._get_value(initial_profile, "total_missing_values", 0),
                    self._get_value(final_profile, "total_missing_values", 0),
                ),
                self._format_transition(
                    "Duplicate Rows",
                    self._get_value(initial_profile, "duplicate_rows", 0),
                    self._get_value(final_profile, "duplicate_rows", 0),
                ),
                self._format_transition(
                    "Validators Passed",
                    initial_passed,
                    final_passed,
                ),
                self._format_transition(
                    "Validators Failed",
                    initial_failed,
                    final_failed,
                ),
            ]
        )

    def _render_summary(
        self,
        validation_results: Iterable[Any],
        healing_results: Iterable[Any],
    ) -> str:
        results = list(validation_results)
        healers = list(healing_results)
        passed, failed = self._count_validation_statuses(results)

        return "\n".join(
            [
                "====================================================",
                "SUMMARY",
                "====================================================",
                "",
                self._format_metric("Total Validators", len(results)),
                self._format_metric("Passed", passed),
                self._format_metric("Failed", failed),
                self._format_metric("Healers Run", len(healers)),
                "",
                "====================================================",
            ]
        )

    def _format_metric(self, label: str, value: Any) -> str:
        return f"{label:<20}: {value}"

    def _format_transition(self, label: str, before: Any, after: Any) -> str:
        return f"{label:<20}: {before} -> {after}"

    def _count_validation_statuses(
        self,
        validation_results: Iterable[Any],
    ) -> tuple[int, int]:
        results = list(validation_results)
        passed = sum(
            1 for result in results if bool(self._get_value(result, "status", False))
        )
        return passed, len(results) - passed

    def _get_initial_profile(self, pipeline_result: Any) -> Any:
        return self._get_value(
            pipeline_result,
            "initial_profile",
            self._get_value(pipeline_result, "profile_result", None),
        )

    def _get_final_profile(self, pipeline_result: Any) -> Any:
        return self._get_value(
            pipeline_result,
            "final_profile",
            self._get_initial_profile(pipeline_result),
        )

    def _get_initial_validation(self, pipeline_result: Any) -> list[Any]:
        results = self._get_value(
            pipeline_result,
            "initial_validation",
            self._get_value(pipeline_result, "validation_results", []),
        )
        if results is None:
            return []
        return list(results)

    def _get_final_validation(self, pipeline_result: Any) -> list[Any]:
        results = self._get_value(
            pipeline_result,
            "final_validation",
            self._get_initial_validation(pipeline_result),
        )
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
