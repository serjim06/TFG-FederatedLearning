from src.application.dto.operation_result import OperationResult
from src.application.repositories.project_repository import ProjectRepository
from src.application.repositories.user_repository import UserRepository


class DeleteUserUseCase:
    """Delete one user and all associated projects."""

    def __init__(
        self,
        user_repository: UserRepository,
        project_repository: ProjectRepository,
    ):
        self.user_repository = user_repository
        self.project_repository = project_repository

    def execute(self, user_id: bytes) -> OperationResult[None]:
        """Delete related projects first, then delete user."""
        user = self.user_repository.get_by_id(user_id)
        if not user:
            return OperationResult(ok=False, error="No se encontró el usuario.")
        projects = self.project_repository.list_by_user(user_id)
        for project in projects:
            self.project_repository.delete(project["id"])
        self.user_repository.delete(user_id)
        return OperationResult(ok=True)
