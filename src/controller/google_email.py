import json
import logging

import httpx

from src.core import encode_access_token, mongo
from src.models.google_auth import GoogleUser, GoogleUserInfo
from src.secrets import secrets
from src.utils import constant
from src.process import Gmail_processor

CLIENT_ID = secrets["google_client_id"]
CLIENT_SECRET = secrets["google_client_secret"]
AUTHENTICATION_URL = secrets["google_authentication_url"]
REDIRECT_URI = secrets["google_redirect_uri"]
TOKEN_URL = secrets["google_token_url"]
USER_INFO_URL = secrets["google_user_info_url"]
SOCIAL_AUTH_REDIRECTION_URL = secrets["social_auth_redirection_url"]
EMAIL_URL = "https://www.googleapis.com/gmail/v1/users/me/messages"
MONGO_URI = "mongodb+srv://dev_rw:S04QlFMrp3XiN9T1@beau-dev-mb-db.gyfxw.mongodb.net/"
BureauEYEDB = "BureauEYE"

def get_email(context,token: str) -> (int, dict):
    try:
        logging.info("Starting to get email")
        headers = {"Authorization":"Bearer "+token}
        params = {
            'q': 'newer_than:20d',
        }
        response = httpx.get(EMAIL_URL, headers=headers, timeout=25, params=params)
        logging.info("response")
        logging.info(response)
        # Check if the response status code is not 200 OK
        if response.status_code != 200:
            logging.error(
                {**context, "message": f"Error fetching token: {response.text}"}
            )
            return response.status_code, {"message": response.text}
        response = response.json()
        logging.info(response)
        data = response["messages"]
        next_token = response.get("nextPageToken", "")
        while next_token != "" :
            #call the next batch
            params['pageToken'] = next_token 
            response = httpx.get(EMAIL_URL, headers=headers, timeout=25, params=params)
            if response.status_code != 200:
                logging.error(
                    {**context, "message": f"Error fetching token: {response.text}"}
                )
            response = response.json()
            logging.info(response)
            data.extend(response["messages"])
            next_token = response.get("nextPageToken", "")
        #store to DB after processing
        Gmail_processor.gmail_processor(context, token, MONGO_URI, BureauEYEDB, data)
        return response.status_code, {"message": data}
    except Exception:
        logging.exception({**context, "message": "Error while getting email"})
        frontend_redirect_url = f"{SOCIAL_AUTH_REDIRECTION_URL}?status=FAILURE"
        return 302, {"location": frontend_redirect_url}
