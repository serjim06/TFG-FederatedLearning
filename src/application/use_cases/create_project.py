import json
import uuid
from typing import Any

from src.application.dto.operation_result import OperationResult
from src.application.repositories.node_repository import NodeRepository
from src.application.repositories.project_repository import ProjectRepository


class CreateProjectUseCase:
    """Create one project and synchronize selected nodes."""

    def __init__(
        self,
        project_repository: ProjectRepository,
        node_repository: NodeRepository,
    ):
        self.project_repository = project_repository
        self.node_repository = node_repository

    def execute(self, user_id: bytes, form_data: dict[str, Any]) -> OperationResult[dict[str, Any]]:
        """Persist a new project from normalized form data."""
        payload = {
            "uid": user_id,
            "name": form_data["name"],
            "description": form_data["description"],
            "parameters": json.dumps(form_data["parameters"]),
            "aggregation_strategy": form_data["aggregation_strategy"],
            "metrics": form_data["metrics"],
            "model_path": form_data["model_path"],
            "input_features": json.dumps(form_data["input_features"]),
            "output_features": json.dumps(form_data["output_features"]),
            "unconfirmed_results": json.dumps([]),
            "type": form_data["task_type"],
        }
        project_row = self.project_repository.create(payload)
        selected_nodes = form_data["initial_nodes"]
        for node_id in selected_nodes:
            self.node_repository.update(
                {
                    "id": uuid.UUID(node_id).bytes,
                    "valid": 1,
                    "project_id": project_row["id"],
                }
            )
        return OperationResult(ok=True, data=project_row)
