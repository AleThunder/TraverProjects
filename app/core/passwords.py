from base64 import urlsafe_b64decode, urlsafe_b64encode
from hashlib import pbkdf2_hmac, sha256
from hmac import compare_digest
from secrets import token_bytes


PASSWORD_ITERATIONS = 210_000


def hash_password(password: str) -> str:
    """Hash a plain password with PBKDF2-HMAC and a random salt."""
    salt = token_bytes(16)
    password_hash = pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PASSWORD_ITERATIONS)
    return f"pbkdf2_sha256${PASSWORD_ITERATIONS}${_encode_bytes(salt)}${_encode_bytes(password_hash)}"


def verify_password(password: str, stored_password: str) -> bool:
    """Compare a plain password with a stored PBKDF2 password hash."""
    try:
        algorithm, iterations, encoded_salt, encoded_hash = stored_password.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        salt = _decode_bytes(encoded_salt)
        expected_hash = _decode_bytes(encoded_hash)
        actual_hash = pbkdf2_hmac("sha256", password.encode("utf-8"), salt, int(iterations))
    except (ValueError, TypeError):
        return False
    return compare_digest(actual_hash, expected_hash)


def hash_session_token(token: str) -> str:
    """Hash a session token before storing it in the database."""
    return sha256(token.encode("utf-8")).hexdigest()


def _encode_bytes(value: bytes) -> str:
    """Encode bytes into a URL-safe string without padding."""
    return urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _decode_bytes(value: str) -> bytes:
    """Decode URL-safe strings produced by the password hashing helper."""
    padding = "=" * (-len(value) % 4)
    return urlsafe_b64decode(value + padding)
