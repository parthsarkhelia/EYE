import logging
from datetime import datetime, timedelta
from typing import Union

import jwt
from fastapi import Header, HTTPException, Request

from src.secrets import secrets

from .encrypt import hash_token
from .mongo_client import mongo

SECRET_KEY = secrets["jwt_secret_key"]
ALGORITHM = secrets["jwt_encode_algorithm"]
ACCESS_TOKEN_EXPIRE_MINUTES = secrets["jwt_token_expiry"]


def get_token_from_query(request: Request):
    token = request.query_params.get("token")
    if not token:
        raise HTTPException(status_code=400, detail="Token is missing.")
    return token


def jwt_dependency(authorization: str = Header(default=None, alias="Authorization")):
    try:
        if not authorization or "Bearer" not in authorization:
            raise HTTPException(status_code=403, detail="Not authenticated")

        token = authorization.split(" ")[1]
        try:
            payload = decode_access_token(token)
        except Exception:
            logging.exception({"message": "Error while decoding access token"})
            raise HTTPException(status_code=400, detail="Invalid token")
        if is_blacklisted(token):
            raise HTTPException(status_code=401, detail="Token has been revoked")
        return payload.get("username")
    except Exception:
        logging.exception({"message": "Error while authenticating user"})
        raise HTTPException(status_code=403, detail="Not authenticated")


def encode_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str, verify: bool = True) -> Union[dict, str]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], verify=verify)
        return payload
    except jwt.ExpiredSignatureError:
        raise Exception("Token has expired")
    except Exception:
        raise Exception("Failed to decode access token")


def is_blacklisted(token: str) -> bool:
    try:
        blacklist_collection = mongo.blacklisted_collection
        token_data = blacklist_collection.find_one({"token": hash_token(token)})
        return bool(token_data)
    except Exception:
        logging.exception({"message": "Error while checking token in blacklist"})
        raise Exception("Error checking token in blacklist")
