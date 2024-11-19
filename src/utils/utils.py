import logging
from datetime import datetime, timedelta
import uuid
from typing import Dict
import requests
import json
from http import HTTPStatus
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
    
def create_response(
    status: str,
    message: str,
    error: str=None,
    response=None,
) -> dict:
    """Create a standardized API response"""
    response = {
        "status": status,
        "timestamp": datetime.utcnow().isoformat(),
        "requestId": str(uuid.uuid4())
    }

    if response is not None:
        response["response"] = response

    if error:
        response["error"] = error

    if message:
        response["message"] = message

    return response

def do_http_request(
    url: str, 
    headers: Dict[str, str], 
    request_body: Dict,
    request_type: str
) -> Dict:
    try:
        payload = json.dumps(request_body)
        response = requests.request(request_type, url, headers=headers, data=payload)
        
        if response.status_code == HTTPStatus.OK:
            return create_response(
                status="success",
                message="success",
                response=response,
            ) 
        elif response.status_code == HTTPStatus.UNAUTHORIZED:
            return create_response(
                status="error",
                error="Unauthorized",
                message="Invalid authentication credentials",
                response=response
            )
            
        elif response.status_code == HTTPStatus.BAD_REQUEST:
            return create_response(
                status="error",
                error="Bad Request",
                message=response.json().get('message', 'Invalid request parameters'),
                response=response
            )
        elif response.status_code == HTTPStatus.CONFLICT:
            return create_response(
                status="error",
                error="Conflict",
                message=response.json().get('message', 'SessionId Already Present!'),
                response=response
            )
        elif response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY:
            return create_response(
                status="error",
                error="Unprocessable Entity",
                message=response.json().get('message', 'SessionId Not Found!'),
                response=response
            )
        else:
            return create_response(
                status="error",
                error=f"API Error: Status Code - {response.status_code}",
                message=f"Service returned message: {response.json()}",
                response=response
            )           
    except requests.exceptions.RequestException as e:
        return {
            "status": "error",
            "error": "Request Error",
            "response": response
        }
    
    except Exception as e:
        logging.exception({"message": "issue faced during http"})
        return {
            "status": "error",
            "error": "Internal Server Error", 
            "response": response
        }
