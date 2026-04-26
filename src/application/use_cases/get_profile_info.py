from src.application.dto.operation_result import OperationResult
from src.application.repositories.project_repository import ProjectRepository
from src.application.repositories.user_repository import UserRepository


class GetProfileInfoUseCase:
    """Return full profile information plus owned projects count."""

    def __init__(
        self,
        user_repository: UserRepository,
        project_repository: ProjectRepository,
    ):
        self.user_repository = user_repository
        self.project_repository = project_repository

    def execute(self, user_id: bytes) -> OperationResult[dict]:
        """Load persisted profile data for one user id."""
        user_row = self.user_repository.get_by_id(user_id)
        if not user_row:
            return OperationResult(ok=False, error="No se pudo cargar el perfil actual")
        projects = self.project_repository.list_by_user(user_id)
        return OperationResult(
            ok=True,
            data={
                "id": user_row["id"],
                "username": user_row["username"],
                "role": user_row["role"],
                "password_hash": user_row.get("password_hash"),
                "recovery_phrase_hash": user_row.get("recovery_phrase_hash"),
                "project_count": len(projects),
            },
        )
