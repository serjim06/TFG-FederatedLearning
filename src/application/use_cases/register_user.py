from src.application.dto.operation_result import OperationResult
from src.application.repositories.user_repository import UserRepository
from src.db.dbcon import sqlite_timestamp_now
from src.security.passwords import hash_password


class RegisterUserUseCase:
    """Register one local user with password and recovery phrase hashes."""

    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    def execute(
        self,
        username: str,
        password: str,
        password_confirm: str,
        recovery_phrase: str,
        recovery_confirm: str,
    ) -> OperationResult[dict]:
        """Create one user if validations pass."""
        username = (username or "").strip()
        password = (password or "").strip()
        password_confirm = (password_confirm or "").strip()
        recovery_phrase = (recovery_phrase or "").strip()
        recovery_confirm = (recovery_confirm or "").strip()
        if not username or not password or not password_confirm or not recovery_phrase or not recovery_confirm:
            return OperationResult(ok=False, error="Rellena todos los campos")
        if password != password_confirm:
            return OperationResult(ok=False, error="Las contraseñas no coinciden")
        if recovery_phrase != recovery_confirm:
            return OperationResult(ok=False, error="Las frases de recuperación no coinciden")
        existing = self.user_repository.get_by_username(username)
        if existing:
            return OperationResult(ok=False, error="El usuario ya existe")
        user = self.user_repository.create(
            {
                "username": username,
                "password_hash": hash_password(password),
                "recovery_phrase_hash": hash_password(recovery_phrase),
                "role": "user",
                "creation_date": sqlite_timestamp_now(),
            }
        )
        return OperationResult(ok=True, data=user)
