import uuid
from typing import Any

from src.projects.reports import generate_report


class ReportService:
    """Generate project reports independent from GUI."""

    def generate_project_report(self, project_row: dict[str, Any], output_path: str) -> None:
        """Create one PDF report for project training data."""
        generate_report(
            str(uuid.UUID(bytes=project_row["id"])),
            project_row["name"],
            project_row["description"],
            project_row["training_round"],
            project_row["type"],
            project_row["training_results"],
            output_path,
        )
