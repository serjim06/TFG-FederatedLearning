import hashlib
import hmac
import secrets


PBKDF2_ITERATIONS = 120_000
SALT_BYTES = 16


def hash_password(plain_text: str) -> str:
    """Return a PBKDF2 hash for the provided plain text value."""
    raw = (plain_text or "").strip()
    if not raw:
        raise ValueError("Password value cannot be empty.")
    salt = secrets.token_bytes(SALT_BYTES)
    digest = hashlib.pbkdf2_hmac("sha256", raw.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(plain_text: str, stored_hash: str) -> bool:
    """Validate a plain text value against a stored PBKDF2 hash."""
    raw = (plain_text or "").strip()
    if not raw or not stored_hash:
        return False
    try:
        algorithm, rounds_text, salt_hex, digest_hex = stored_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        rounds = int(rounds_text)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(digest_hex)
    except (ValueError, TypeError):
        return False
    current = hashlib.pbkdf2_hmac("sha256", raw.encode("utf-8"), salt, rounds)
    return hmac.compare_digest(current, expected)
