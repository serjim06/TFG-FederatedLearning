import os
import shutil

from src.application.dto.operation_result import OperationResult
from src.application.repositories.node_repository import NodeRepository
from src.models.node import Node


class ManageNodesUseCase:
    """Handle node list/create/delete operations for GUI."""

    def __init__(self, node_repository: NodeRepository):
        self.node_repository = node_repository

    def list_all(self) -> OperationResult[list[dict]]:
        """Return all persisted nodes."""
        return OperationResult(ok=True, data=self.node_repository.list_all())

    def create(self) -> OperationResult[dict]:
        """Create one node and persist computed dataset path."""
        node_row = self.node_repository.create(
            {"valid": 0, "project_id": "", "local_dataset_path": ""}
        )
        node = Node(node_row["id"], node_row["valid"], node_row["local_dataset_path"])
        self.node_repository.update({"id": node.id, "local_dataset_path": node.local_dataset_path})
        updated = self.node_repository.get_by_id(node.id)
        return OperationResult(ok=True, data=updated)

    def delete(self, node_id: bytes) -> OperationResult[None]:
        """Delete one node and its local dataset by id."""
        node_row = self.node_repository.get_by_id(node_id)
        if not node_row:
            return OperationResult(ok=False, error="No se encontró el nodo a eliminar.")

        dataset_path = node_row.get("local_dataset_path") or ""
        if dataset_path and os.path.exists(dataset_path):
            try:
                shutil.rmtree(dataset_path)
            except OSError as exc:
                return OperationResult(
                    ok=False,
                    error=f"No se pudo eliminar el dataset asociado al nodo: {exc}",
                )

        self.node_repository.delete(node_id)
        return OperationResult(ok=True)
