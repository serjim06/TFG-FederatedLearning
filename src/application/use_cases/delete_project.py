from typing import Callable

from src.application.dto.operation_result import OperationResult
from src.application.repositories.node_repository import NodeRepository
from src.application.repositories.project_repository import ProjectRepository


class DeleteProjectUseCase:
    """Delete one project and invalidate its assigned nodes."""

    def __init__(
        self,
        project_repository: ProjectRepository,
        node_repository: NodeRepository,
    ):
        self.project_repository = project_repository
        self.node_repository = node_repository

    def execute(
        self,
        project_id: bytes,
        on_node_removed: Callable[[bytes], None] | None = None,
        on_node_update_error: Callable[[Exception], None] | None = None,
    ) -> OperationResult[None]:
        """Delete project after invalidating nodes and removing related datasets."""
        project_nodes = self.node_repository.list_by_project_id(project_id)
        for node_row in project_nodes:
            if on_node_removed is not None:
                on_node_removed(node_row["id"])
            try:
                self.node_repository.update({"id": node_row["id"], "valid": 0, "project_id": ""})
            except Exception as exc:
                if on_node_update_error is not None:
                    on_node_update_error(exc)
        self.project_repository.delete(project_id)
        return OperationResult(ok=True)
