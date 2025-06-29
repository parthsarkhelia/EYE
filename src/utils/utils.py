import json
import logging
import uuid
from datetime import datetime, timedelta
from http import HTTPStatus
from typing import Dict

import jwt
import requests

from src.secrets import secrets
from src.utils import constant


def get_package_names(user_application_list):
    package_names = []
    for app in user_application_list:
        package_names.append(app["packageName_"])
    return package_names


def get_account_list(signals_output):
    account_list = []
    if signals_output[constant.PHONE_WHATSAPP] == "Account Found":
        account_list.append(constant.PHONE_WHATSAPP)
    if signals_output[constant.PHONE_INSTAGRAM] == "Account Found":
        account_list.append(constant.PHONE_INSTAGRAM)
    if signals_output[constant.PHONE_AMAZON] == "Account Found":
        account_list.append(constant.PHONE_AMAZON)
    if signals_output[constant.PHONE_PAYTM] == "Account Found":
        account_list.append(constant.PHONE_PAYTM)
    if signals_output[constant.PHONE_FLIPKART] == "Account Found":
        account_list.append(constant.PHONE_FLIPKART)
    if signals_output[constant.PHONE_INDIAMART] == "Account Found":
        account_list.append(constant.PHONE_INDIAMART)
    if signals_output[constant.PHONE_JEEVANSAATHI] == "Account Found":
        account_list.append(constant.PHONE_JEEVANSAATHI)
    if signals_output[constant.PHONE_JIOMART] == "Account Found":
        account_list.append(constant.PHONE_JIOMART)
    if signals_output[constant.PHONE_SHAADI] == "Account Found":
        account_list.append(constant.PHONE_SHAADI)
    if signals_output[constant.PHONE_SWIGGY] == "Account Found":
        account_list.append(constant.PHONE_SWIGGY)
    if signals_output[constant.PHONE_TOI] == "Account Found":
        account_list.append(constant.PHONE_TOI)
    if signals_output[constant.PHONE_YATRA] == "Account Found":
        account_list.append(constant.PHONE_YATRA)
    if signals_output[constant.PHONE_ZOHO] == "Account Found":
        account_list.append(constant.PHONE_ZOHO)
    if signals_output[constant.PHONE_WHATSAPPBUSINESS] == "Account Found":
        account_list.append(constant.PHONE_WHATSAPPBUSINESS)

    return account_list


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
    error: str = None,
    resp=None,
) -> dict:
    response = {
        "status": status,
        "timestamp": datetime.utcnow().isoformat(),
        "requestId": str(uuid.uuid4()),
    }

    if resp is not None:
        response["response"] = resp

    if error:
        response["error"] = error

    if message:
        response["message"] = message

    return response


def do_http_request(
    url: str, headers: Dict[str, str], request_body: Dict, request_type: str
) -> Dict:
    try:
        payload = json.dumps(request_body)
        response = requests.request(request_type, url, headers=headers, data=payload)
        if response.status_code != HTTPStatus.OK:
            error_response = json.loads(response.content.decode("utf-8"))
            error = "API Error"
            message = "Internal Server Error"
            if response.status_code == HTTPStatus.UNAUTHORIZED:
                error = "Unauthorized"
                message = "Invalid authentication credentials"
            elif response.status_code == HTTPStatus.BAD_REQUEST:
                error = "Bad Request"
                message = "Invalid request parameters"
            elif response.status_code == HTTPStatus.CONFLICT:
                error = "Conflict"
                message = "SessionId Already Present!"
            elif response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY:
                error = "Unprocessable Entity"
                message = "SessionId Not Found!"

            return create_response(
                status="error",
                error=error,
                message=message,
                resp=error_response,
            )
        else:
            resp = None
            if response.text:
                resp = json.loads(response.text)
            return create_response(
                status="success",
                message="success",
                resp=resp,
            )
    except requests.exceptions.RequestException:
        logging.exception({"message": "panic with request exception"})
        return {
            "status": "error",
            "error": "Request Error",
            "message": "internal error",
        }
    except Exception as e:
        logging.exception({"message": "issue faced during http"})
        return {"status": "error", "error": str(e), "message": "internal server error"}
