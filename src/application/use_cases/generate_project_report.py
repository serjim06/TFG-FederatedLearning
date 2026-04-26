from src.application.dto.operation_result import OperationResult
from src.application.repositories.project_repository import ProjectRepository
from src.application.services.report_service import ReportService


class GenerateProjectReportUseCase:
    """Generate one project PDF report from persisted training data."""

    def __init__(
        self,
        project_repository: ProjectRepository,
        report_service: ReportService,
    ):
        self.project_repository = project_repository
        self.report_service = report_service

    def execute(self, project_id: bytes, output_path: str) -> OperationResult[None]:
        """Generate report or return an actionable error."""
        project_row = self.project_repository.get_by_id(project_id)
        if not project_row:
            return OperationResult(ok=False, error="No se han encontrado datos del proyecto para generar el reporte.")
        self.report_service.generate_project_report(project_row, output_path)
        return OperationResult(ok=True)
