from abc import ABC, abstractmethod
from typing import Any


class NodeRepository(ABC):
    """Define persistence operations for nodes."""

    @abstractmethod
    def list_all(self) -> list[dict[str, Any]]:
        """Return all nodes."""

    @abstractmethod
    def list_available(self) -> list[dict[str, Any]]:
        """Return available nodes for assignment."""

    @abstractmethod
    def list_by_project_id(self, project_id: bytes) -> list[dict[str, Any]]:
        """Return active nodes assigned to one project."""

    @abstractmethod
    def get_by_id(self, node_id: bytes) -> dict[str, Any] | None:
        """Return one node row or None."""

    @abstractmethod
    def create(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Persist and return one new node row."""

    @abstractmethod
    def update(self, payload: dict[str, Any]) -> None:
        """Update node fields."""

    @abstractmethod
    def delete(self, node_id: bytes) -> None:
        """Delete one node."""
