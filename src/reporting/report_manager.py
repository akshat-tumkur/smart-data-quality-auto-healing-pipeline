"""Management helpers for generating and saving quality reports."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any


class ReportManager:
    """Coordinate report generation and persistence."""

    def __init__(self, generator: Any) -> None:
        """Store the report generator used to build report content."""

        self.generator = generator

    def generate_report(self, pipeline_result: Any) -> str:
        """Generate a report string from the supplied pipeline result."""

        return self.generator.generate(pipeline_result)

    def save(self, report: str, output_directory: str = "reports") -> str:
        """Save a report to a timestamped UTF-8 text file and return its path."""

        output_path = Path(output_directory)
        output_path.mkdir(parents=True, exist_ok=True)

        filename = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        report_path = output_path / filename
        report_path.write_text(report, encoding="utf-8")
        return str(report_path)