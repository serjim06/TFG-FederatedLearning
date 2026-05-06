from typing import Any

from src.application.repositories.node_repository import NodeRepository
from src.db import dbcon


class SQLiteNodeRepository(NodeRepository):
    """SQLite implementation of node repository."""

    def list_all(self) -> list[dict[str, Any]]:
        return dbcon.command("select", "nodes", {"id": "*"})

    def list_available(self) -> list[dict[str, Any]]:
        return dbcon.command("select", "nodes", {"id": "*", "valid": 0})

    def list_by_project_id(self, project_id: bytes) -> list[dict[str, Any]]:
        return dbcon.command("select", "nodes", {"project_id": project_id, "valid": 1})

    def get_by_id(self, node_id: bytes) -> dict[str, Any] | None:
        rows = dbcon.command("select", "nodes", {"id": node_id})
        return rows[0] if rows else None

    def create(self, payload: dict[str, Any]) -> dict[str, Any]:
        created = dbcon.command("insert", "nodes", payload)
        return {"id": created[0], "valid": created[1], "local_dataset_path": created[2]}

    def update(self, payload: dict[str, Any]) -> None:
        dbcon.command("update", "nodes", payload)

    def delete(self, node_id: bytes) -> None:
        dbcon.command("delete", "nodes", {"id": node_id})
