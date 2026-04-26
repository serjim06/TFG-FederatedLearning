from abc import ABC, abstractmethod
from typing import Any


class UserRepository(ABC):
    """Define persistence operations for user entities."""

    @abstractmethod
    def list_all(self) -> list[dict[str, Any]]:
        """Return all users."""

    @abstractmethod
    def get_by_id(self, user_id: bytes) -> dict[str, Any] | None:
        """Return one user by id or None."""

    @abstractmethod
    def get_by_username(self, username: str) -> dict[str, Any] | None:
        """Return one user by username or None."""

    @abstractmethod
    def create(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Persist one user and return inserted row."""

    @abstractmethod
    def update(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Update one user and return updated row."""

    @abstractmethod
    def delete(self, user_id: bytes) -> None:
        """Delete one user by id."""
