from src.application.dto.operation_result import OperationResult
from src.application.repositories.user_repository import UserRepository
from src.security.passwords import hash_password


class UpdateUserProfileUseCase:
    """Apply username, password and recovery phrase profile changes."""

    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    def execute(
        self,
        user_id: bytes,
        username: str,
        password: str,
        password_confirm: str,
        recovery_phrase: str,
        recovery_confirm: str,
    ) -> OperationResult[dict]:
        """Persist profile changes and return updated user row."""
        username = (username or "").strip()
        password = (password or "").strip()
        password_confirm = (password_confirm or "").strip()
        recovery_phrase = (recovery_phrase or "").strip()
        recovery_confirm = (recovery_confirm or "").strip()
        if not username:
            return OperationResult(ok=False, error="El usuario no puede estar vacío")
        current = self.user_repository.get_by_id(user_id)
        if not current:
            return OperationResult(ok=False, error="No se pudo cargar la cuenta actual")
        update_payload = {"id": user_id}
        if username != current["username"]:
            update_payload["username"] = username
        if password or password_confirm:
            if password != password_confirm:
                return OperationResult(ok=False, error="Las contraseñas no coinciden")
            update_payload["password_hash"] = hash_password(password)
        if recovery_phrase or recovery_confirm:
            if recovery_phrase != recovery_confirm:
                return OperationResult(ok=False, error="Las frases de recuperación no coinciden")
            update_payload["recovery_phrase_hash"] = hash_password(recovery_phrase)
        if len(update_payload) == 1:
            return OperationResult(ok=False, error="No hay cambios para guardar")
        updated = self.user_repository.update(update_payload)
        return OperationResult(ok=True, data=updated)
