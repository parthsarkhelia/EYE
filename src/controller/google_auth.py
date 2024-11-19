import json
import logging

import httpx

from src.core import encode_access_token, mongo
from src.models.google_auth import GoogleUser, GoogleUserInfo
from src.secrets import secrets
from src.utils import constant
from src.controller.google_email import get_email

CLIENT_ID = secrets["google_client_id"]
CLIENT_SECRET = secrets["google_client_secret"]
AUTHENTICATION_URL = secrets["google_authentication_url"]
REDIRECT_URI = secrets["google_redirect_uri"]
TOKEN_URL = secrets["google_token_url"]
USER_INFO_URL = secrets["google_user_info_url"]
SOCIAL_AUTH_REDIRECTION_URL = secrets["social_auth_redirection_url"]


def get_google_auth_url(context) -> (int, dict):
    try:
        params = {
            "client_id": CLIENT_ID,
            "redirect_uri": REDIRECT_URI,
            "response_type": "code",
            "scope": "openid%20email%20profile",
        }

        auth_url = f"{AUTHENTICATION_URL}?" + "&".join(
            [f"{key}={value}" for key, value in params.items()]
        )

        return 200, {
            "message": constant.GOOGLE_AUTH_URL_SUCCESS,
            "auth_url": auth_url,
        }
    except Exception:
        logging.exception({**context, "message": "Error while generating auth URL"})
        return 400, {"message": constant.PROCESSING_ERROR}


def authenticate_google_user(context, code: str) -> (int, dict):
    try:
        data = {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "grant_type": "authorization_code",
            "redirect_uri": REDIRECT_URI,
            "scope":"https://www.googleapis.com/auth/gmail.readonly",
            "code": code,
        }

        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        response = httpx.post(TOKEN_URL, data=data, headers=headers, timeout=25)

        # Check if the response status code is not 200 OK
        if response.status_code != 200:
            logging.error(
                {**context, "message": f"Error fetching token: {response.text}"}
            )
            return response.status_code, {"message": response.text}

        token_data = response.json()
        access_token = token_data.get("access_token")
        logging.info({**context, "access_token": access_token})
        if not access_token:
            logging.error(
                {
                    **context,
                    "message": f"Access token not found in response: {token_data}",
                }
            )
            return 400, {"message": constant.PROCESSING_ERROR}
        
        
        headers = {"Authorization": f"Bearer {access_token}"}
        # call get email
        status_code, resp = get_email(context, access_token)
        logging.info({"getEmailOutput": resp})
        
        # user_info_response = httpx.get(USER_INFO_URL, headers=headers, timeout=25)
        # if user_info_response.status_code != 200:
        #     logging.error(
        #         {
        #             **context,
        #             "message": f"Error fetching user info: {user_info_response.text}",
        #         }
        #     )
        #     return user_info_response.status_code, {"message": user_info_response.text}

        # user_info = user_info_response.json()
        # logging.info(
        #     {**context, "message": f"UserInfo Response: {json.dumps(user_info)}"}
        # )
        # user_info = GoogleUserInfo(**user_info)
        # username = store_google_user(context, user_info)

        # access_token = encode_access_token(data={"username": username})
        frontend_redirect_url = f"{SOCIAL_AUTH_REDIRECTION_URL}?status=SUCCESS&access_token={access_token}&token_type=bearer"
        return 302, {"location": frontend_redirect_url}

    except Exception:
        logging.exception({**context, "message": "Error while authenticating user"})
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
