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
        response = httpx.get(EMAIL_URL, headers=headers, timeout=25)
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
        next_token = response["nextPageToken"]
        while next_token != "" :
            #call the next batch
            response = httpx.get(EMAIL_URL+"?pageToken="+next_token, headers=headers, timeout=25)
            if response.status_code != 200:
                logging.error(
                    {**context, "message": f"Error fetching token: {response.text}"}
                )
            response = response.json()
            logging.info(response)
            data.extend(response["messages"])
            next_token = response["nextPageToken"]
        #store to DB after processing
        Gmail_processor.gmail_processor(token, MONGO_URI, BureauEYEDB, data)
        return response.status_code, {"message": data}
    except Exception:
        logging.exception({**context, "message": "Error while getting email"})
        frontend_redirect_url = f"{SOCIAL_AUTH_REDIRECTION_URL}?status=FAILURE"
        return 302, {"location": frontend_redirect_url}


def store_google_user(context, user_info: GoogleUserInfo):
    try:
        # Check if a user with the given email already exists
        existing_user = GoogleUser.find_by_email(user_info.email)
        if not existing_user:
            # Create a new GoogleUser instance
            new_google_user = GoogleUser(
                username=user_info.email,
                email=user_info.email,
                first_name=user_info.given_name,
                last_name=user_info.family_name,
                google_id=user_info.sub,
                picture=user_info.picture,
                locale=user_info.locale,
            )

            # Save the new user to the database
            new_google_user.save()

            # Store complete Google profile information in SocialAuth collection
            social_auth_data = user_info.dict()
            social_auth_data["platform"] = "Google"
            mongo.social_auth_collection.insert_one(social_auth_data)
            username = new_google_user.username
        else:
            username = existing_user.username
        logging.info({**context, "message": "Google user stored successfully"})
        return username
    except Exception:
        logging.exception({**context, "message": "Error while storing Google user"})
