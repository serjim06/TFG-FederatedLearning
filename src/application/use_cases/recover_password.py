from src.application.dto.operation_result import OperationResult
from src.application.repositories.user_repository import UserRepository
from src.security.passwords import hash_password, verify_password


class RecoverPasswordUseCase:
    """Recover one user password with recovery phrase verification."""

    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    def load_recoverable_user(self, username: str) -> OperationResult[dict]:
        """Return user row only when recovery phrase is configured."""
        row = self.user_repository.get_by_username((username or "").strip())
        if not row:
            return OperationResult(ok=False, error="Usuario o credenciales de recuperación incorrectos")
        if not row.get("recovery_phrase_hash"):
            return OperationResult(
                ok=False,
                error="Esta cuenta no tiene frase de recuperación configurada. Contacta con administración.",
            )
        return OperationResult(ok=True, data=row)

    def execute(
        self,
        user_id: bytes,
        recovery_phrase: str,
        new_password: str,
        new_password_confirm: str,
    ) -> OperationResult[None]:
        """Update password hash when recovery phrase and password validations pass."""
        recovery_phrase = (recovery_phrase or "").strip()
        new_password = (new_password or "").strip()
        new_password_confirm = (new_password_confirm or "").strip()
        if not recovery_phrase or not new_password or not new_password_confirm:
            return OperationResult(ok=False, error="Rellena todos los campos")
        if new_password != new_password_confirm:
            return OperationResult(ok=False, error="Las contraseñas no coinciden")
        user = self.user_repository.get_by_id(user_id)
        if not user:
            return OperationResult(ok=False, error="Usuario o credenciales de recuperación incorrectos")
        if not verify_password(recovery_phrase, user.get("recovery_phrase_hash")):
            return OperationResult(ok=False, error="Usuario o credenciales de recuperación incorrectos")
        self.user_repository.update({"id": user_id, "password_hash": hash_password(new_password)})
        return OperationResult(ok=True)
