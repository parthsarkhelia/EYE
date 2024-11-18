from datetime import datetime, timedelta

import jwt

from src.secrets import secrets


def generate_token(payload: dict, expiration_hours: int = 24) -> str:
    """
    Generates a JWT token using the provided payload and expiration duration.
    :param payload: The dictionary payload to encode into the JWT.
    :param expiration_hours: The duration for which the token remains valid (default is 24 hours).
    :return: Encoded JWT token.
    """
    payload["exp"] = datetime.utcnow() + timedelta(hours=expiration_hours)
    payload["iat"] = datetime.utcnow()
    return jwt.encode(
        payload, secrets["jwt_secret_key"], algorithm=secrets["jwt_encode_algorithm"]
    )
