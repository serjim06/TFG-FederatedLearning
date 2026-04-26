import json
import uuid
from typing import Any, Callable

from src.application.dto.operation_result import OperationResult
from src.application.repositories.node_repository import NodeRepository
from src.application.repositories.project_repository import ProjectRepository


class UpdateProjectUseCase:
    """Update one existing project and reconcile node assignments."""

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
        previous_project_row: dict[str, Any],
        form_data: dict[str, Any],
        on_node_removed: Callable[[bytes], None] | None = None,
    ) -> OperationResult[dict[str, Any]]:
        """Persist project edition and synchronize node states."""
        update_payload = {
            "id": project_id,
            "uid": previous_project_row["uid"],
            "name": form_data["name"],
            "description": form_data["description"],
            "parameters": json.dumps(form_data["parameters"]),
            "aggregation_strategy": form_data["aggregation_strategy"],
            "metrics": form_data["metrics"],
        }
        project_row = self.project_repository.update(update_payload)
        old_nodes = {
            node["id"] for node in self.node_repository.list_by_project_id(project_id)
        }
        new_nodes = {uuid.UUID(node_id).bytes for node_id in form_data["initial_nodes"]}
        removed = old_nodes - new_nodes
        for node_id in removed:
            if on_node_removed is not None:
                on_node_removed(node_id)
            self.node_repository.update({"id": node_id, "valid": 0})
        for node_id in new_nodes:
            self.node_repository.update({"id": node_id, "valid": 1, "project_id": project_id})
        return OperationResult(ok=True, data=project_row)
