from typing import Any

from src.application.dto.operation_result import OperationResult
from src.application.repositories.project_repository import ProjectRepository
from src.application.repositories.user_repository import UserRepository


class ListManagedUsersUseCase:
    """List users for admin management with derived project counters."""

    def __init__(
        self,
        user_repository: UserRepository,
        project_repository: ProjectRepository,
    ):
        self.user_repository = user_repository
        self.project_repository = project_repository

    def execute(self, current_user_id: bytes) -> OperationResult[list[dict[str, Any]]]:
        """Return all users except the current one plus project counts."""
        users = self.user_repository.list_all()
        out = []
        for user in users:
            if user["id"] == current_user_id:
                continue
            n_projects = len(self.project_repository.list_by_user(user["id"]))
            out.append(
                {
                    "id": user["id"],
                    "username": user["username"],
                    "role": user["role"],
                    "password_hash": user.get("password_hash"),
                    "recovery_phrase_hash": user.get("recovery_phrase_hash"),
                    "project_count": n_projects,
                }
            )
        return OperationResult(ok=True, data=out)
