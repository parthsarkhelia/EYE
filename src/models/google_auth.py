from datetime import datetime

from pydantic import BaseModel

from src.core import mongo

from .user import UserBase


class GoogleOAuth2Token(BaseModel):
    access_token: str
    token_type: str
    refresh_token: str
    expires_in: int
    scope: str
    id_token: str


class GoogleUserInfo(BaseModel):
    sub: str
    email: str
    email_verified: bool = False
    name: str = ""
    given_name: str = ""
    family_name: str = ""
    picture: str = ""
    locale: str = ""


class GoogleUser:
    def __init__(
        self, username, email, first_name, last_name, google_id, picture, locale
    ):
        self.username = username
        self.email = email
        self.first_name = first_name
        self.last_name = last_name
        self.google_id = google_id
        self.picture = picture
        self.locale = locale

    def save(self):
        user_data = {
            "username": self.username,
            "email": self.email,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "phone_number": "",
            "dob": "",
            "country": "",
            "hashed_password": "",
            "is_verified": True,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }
        return mongo.user_collection.insert_one(user_data).inserted_id

    @classmethod
    def find_by_email(cls, email):
        result = mongo.user_collection.find_one({"email": email})
        if result:
            return UserBase(**result)
        return None

    @classmethod
    def find_by_google_id(cls, google_id):
        result = mongo.user_collection.find_one({"google_id": google_id})
        if result:
            return UserBase(**result)
        return None
