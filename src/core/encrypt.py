import bcrypt


def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(
        plain_password.encode("utf-8"), hashed_password.encode("utf-8")
    )


def hash_token(token: str) -> bytes:
    """Hashes a token."""
    return bcrypt.hashpw(token.encode("utf-8"), bcrypt.gensalt())


def verify_token_hash(token: str, hashed_token: bytes) -> bool:
    """Verifies a token against its hash."""
    return bcrypt.checkpw(token.encode("utf-8"), hashed_token)
