from typing import Any

from src.application.repositories.project_repository import ProjectRepository
from src.db import dbcon


class SQLiteProjectRepository(ProjectRepository):
    """SQLite implementation of project repository."""

    def get_by_id(self, project_id: bytes) -> dict[str, Any] | None:
        rows = dbcon.command("select", "projects", {"id": project_id})
        return rows[0] if rows else None

    def list_by_user(self, user_id: bytes) -> list[dict[str, Any]]:
        return dbcon.command("select", "projects", {"uid": user_id})

    def create(self, payload: dict[str, Any]) -> dict[str, Any]:
        dbcon.command("insert", "projects", payload)
        rows = dbcon.command(
            "select",
            "projects",
            {"name": payload["name"], "uid": payload["uid"]},
        )
        if not rows:
            raise ValueError("No se pudo recuperar el proyecto recién creado.")
        return rows[0]

    def update(self, payload: dict[str, Any]) -> dict[str, Any]:
        dbcon.command("update", "projects", payload)
        rows = dbcon.command("select", "projects", {"id": payload["id"]})
        if not rows:
            raise ValueError("No se pudo recuperar el proyecto actualizado.")
        return rows[0]

    def delete(self, project_id: bytes) -> None:
        dbcon.command("delete", "projects", {"id": project_id})
