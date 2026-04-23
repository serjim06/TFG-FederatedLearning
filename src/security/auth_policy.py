import time


MIN_PASSWORD_LENGTH = 8
MAX_LOGIN_ATTEMPTS = 5
LOCK_SECONDS = 30
MIN_RECOVERY_PHRASE_LENGTH = 4


def validate_password_strength(password: str) -> None:
    """Raise ValueError when password does not satisfy minimum policy."""
    value = (password or "").strip()
    if len(value) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"La contraseña debe tener al menos {MIN_PASSWORD_LENGTH} caracteres.")
    has_letter = any(ch.isalpha() for ch in value)
    has_digit = any(ch.isdigit() for ch in value)
    if not has_letter or not has_digit:
        raise ValueError("La contraseña debe incluir letras y números.")


def validate_recovery_phrase(phrase: str) -> None:
    """Raise ValueError when recovery phrase is missing or too short."""
    value = (phrase or "").strip()
    if len(value) < MIN_RECOVERY_PHRASE_LENGTH:
        raise ValueError(f"La frase de recuperación debe tener al menos {MIN_RECOVERY_PHRASE_LENGTH} caracteres.")


def get_lock_message(locked_until: float) -> str:
    """Return localized lockout message from a lock-until timestamp."""
    remain = max(1, int(locked_until - time.time()))
    return f"Demasiados intentos fallidos. Inténtalo de nuevo en {remain}s."
