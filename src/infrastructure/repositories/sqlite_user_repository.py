from typing import Any

from src.application.repositories.user_repository import UserRepository
from src.db import dbcon


class SQLiteUserRepository(UserRepository):
    """SQLite implementation of user repository."""

    def list_all(self) -> list[dict[str, Any]]:
        return dbcon.command("select", "users", {"id": "*"})

    def get_by_id(self, user_id: bytes) -> dict[str, Any] | None:
        rows = dbcon.command("select", "users", {"id": user_id})
        return rows[0] if rows else None

    def get_by_username(self, username: str) -> dict[str, Any] | None:
        rows = dbcon.command("select", "users", {"username": username})
        return rows[0] if rows else None

    def create(self, payload: dict[str, Any]) -> dict[str, Any]:
        dbcon.command("insert", "users", payload)
        rows = dbcon.command("select", "users", {"username": payload["username"]})
        if not rows:
            raise ValueError("No se pudo recuperar el usuario recién creado.")
        return rows[0]

    def update(self, payload: dict[str, Any]) -> dict[str, Any]:
        dbcon.command("update", "users", payload)
        rows = dbcon.command("select", "users", {"id": payload["id"]})
        if not rows:
            raise ValueError("No se pudo recuperar el usuario actualizado.")
        return rows[0]

    def delete(self, user_id: bytes) -> None:
        dbcon.command("delete", "users", {"id": user_id})
