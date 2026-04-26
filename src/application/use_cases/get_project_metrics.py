from typing import Any

from src.application.dto.operation_result import OperationResult
from src.application.repositories.node_repository import NodeRepository
from src.application.repositories.project_repository import ProjectRepository
from src.application.services.metrics_service import MetricsService


class GetProjectMetricsUseCase:
    """Load one project and compute metrics payload for UI dialogs."""

    def __init__(
        self,
        project_repository: ProjectRepository,
        node_repository: NodeRepository,
        metrics_service: MetricsService,
    ):
        self.project_repository = project_repository
        self.node_repository = node_repository
        self.metrics_service = metrics_service

    def execute(self, project_id: bytes) -> OperationResult[dict[str, Any]]:
        """Return calculated metrics data for one project id."""
        project_row = self.project_repository.get_by_id(project_id)
        if not project_row:
            return OperationResult(ok=False, error="No se encontró el proyecto.")
        nodes = self.node_repository.list_by_project_id(project_id)
        payload = self.metrics_service.build_project_metrics_payload(project_row, nodes)
        payload["project_row"] = project_row
        return OperationResult(ok=True, data=payload)
