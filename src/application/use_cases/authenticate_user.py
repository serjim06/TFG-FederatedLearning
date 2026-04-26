from src.application.dto.operation_result import OperationResult
from src.application.repositories.user_repository import UserRepository
from src.security.passwords import verify_password


class AuthenticateUserUseCase:
    """Authenticate one user by username and password."""

    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    def execute(self, username: str, password: str) -> OperationResult[dict]:
        """Validate credentials and return user row."""
        row = self.user_repository.get_by_username(username)
        if not row:
            return OperationResult(ok=False, error="Usuario o contraseña incorrectos")
        if not verify_password(password, row.get("password_hash")):
            return OperationResult(ok=False, error="Usuario o contraseña incorrectos")
        return OperationResult(ok=True, data=row)
