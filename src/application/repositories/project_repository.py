from abc import ABC, abstractmethod
from typing import Any


class ProjectRepository(ABC):
    """Define persistence operations for project aggregates."""

    @abstractmethod
    def get_by_id(self, project_id: bytes) -> dict[str, Any] | None:
        """Return one project row or None."""

    @abstractmethod
    def list_by_user(self, user_id: bytes) -> list[dict[str, Any]]:
        """Return all projects owned by one user."""

    @abstractmethod
    def create(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Persist a new project and return the inserted row."""

    @abstractmethod
    def update(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Persist project changes and return the updated row."""

    @abstractmethod
    def delete(self, project_id: bytes) -> None:
        """Delete one project by id."""
