import uuid
from typing import Any, Callable

from src.application.dto.operation_result import OperationResult
from src.application.repositories.node_repository import NodeRepository
from src.application.repositories.project_repository import ProjectRepository
from src.application.repositories.user_repository import UserRepository
from src.application.services.federated_training_service import FederatedTrainingService
from src.db.dbcon import sqlite_timestamp_now
from src.models.node import merge_project_training_results


ProgressCallback = Callable[[int, int, str, float | None], None]


class RunFederatedTrainingUseCase:
    """Run federated rounds and persist resulting project state."""

    def __init__(
        self,
        project_repository: ProjectRepository,
        node_repository: NodeRepository,
        user_repository: UserRepository,
        training_service: FederatedTrainingService,
    ):
        self.project_repository = project_repository
        self.node_repository = node_repository
        self.user_repository = user_repository
        self.training_service = training_service

    def execute(
        self,
        project_id: bytes,
        rounds: int,
        on_progress: ProgressCallback | None = None,
    ) -> OperationResult[dict[str, Any]]:
        """Execute one federated training job for one project."""
        project_row = self.project_repository.get_by_id(project_id)
        if not project_row:
            return OperationResult(ok=False, error="No se encontró el proyecto.")
        nodes = self.node_repository.list_by_project_id(project_id)
        if not nodes:
            return OperationResult(
                ok=False,
                error="El proyecto no tiene nodos asignados. Añade nodos en la configuración del proyecto.",
            )
        node_ids = [str(uuid.UUID(bytes=node["id"])) for node in nodes]
        out = self.training_service.run(
            project_row,
            rounds,
            node_ids=node_ids,
            on_progress=on_progress,
        )
        merged = merge_project_training_results(
            project_row.get("training_results"),
            out["training_results_entry"],
        )
        trained_at = sqlite_timestamp_now()
        update_payload: dict[str, Any] = {"id": project_id, "training_results": merged}
        if not project_row.get("type"):
            update_payload["type"] = (
                "regression"
                if (project_row.get("metrics") or "") == "mean_squared_error"
                else "classification"
            )
        cur_data_round = int(project_row.get("training_round") or 0)
        update_payload["training_round"] = cur_data_round + int(rounds) + 1
        update_payload["updated_at"] = trained_at
        self.project_repository.update(update_payload)
        self.user_repository.update(
            {
                "id": project_row["uid"],
                "last_train": trained_at,
            }
        )
        return OperationResult(
            ok=True,
            data={
                "merged_training_results": merged,
                "total_time_seconds": out["total_time_seconds"],
                "project_row": project_row,
                "rounds": rounds,
            },
        )
