from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from src.core import get_password_hash, hash_token, mongo


class UserBase(BaseModel):
    username: str
    email: EmailStr
    first_name: str
    last_name: str
    phone_number: str = ""
    dob: str = ""
    country: str = ""


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    password: str = None
    email: EmailStr = None
    first_name: str = Field(None, min_length=1)
    last_name: str = Field(None, min_length=1)
    phone_number: str = None
    dob: str = None
    country: str = None


class UserAuthenticate(BaseModel):
    username: str
    password: str


class ForgotPasswordRequest(BaseModel):
    username: str


class PasswordReset(BaseModel):
    password: str


class User:
    def __init__(
        self,
        username,
        email,
        first_name,
        last_name,
        phone_number,
        dob,
        country,
        password=None,
        **kwargs,
    ):
        self.username = username
        self.email = email
        self.first_name = first_name
        self.last_name = last_name
        self.phone_number = phone_number
        self.dob = dob
        self.country = country
        self.hashed_password = (
            get_password_hash(password)
            if password
            else kwargs.get("hashed_password", None)
        )
        self.is_verified = kwargs.get("is_verified", False)
        self.verification_code = kwargs.get("verification_code", None)
        self.reset_token = kwargs.get("reset_token", None)

    def save(self):
        user_data = {
            "username": self.username,
            "email": self.email,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "phone_number": self.phone_number,
            "dob": self.dob,
            "country": self.country,
            "hashed_password": self.hashed_password,
            "is_verified": self.is_verified,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }
        return mongo.user_collection.insert_one(user_data).inserted_id

    def update(self, update_data):
        update_data["updated_at"] = datetime.now()
        mongo.user_collection.update_one(
            {"username": self.username}, {"$set": update_data}
        )

    @classmethod
    def find_by_username(cls, username):
        user_data = mongo.user_collection.find_one({"username": username})
        if user_data:
            return cls(**user_data)
        return None

    @classmethod
    def find_by_email(cls, email):
        user_data = mongo.user_collection.find_one({"email": email})
        if user_data:
            return cls(**user_data)
        return None

    @classmethod
    def set_verification_token(cls, username, token):
        hashed_token = hash_token(token)
        mongo.user_collection.update_one(
            {"username": username}, {"$set": {"verification_code": hashed_token}}
        )

    @classmethod
    def set_reset_token(cls, username, token):
        hashed_token = hash_token(token)
        mongo.user_collection.update_one(
            {"username": username}, {"$set": {"reset_token": hashed_token}}
        )

    def verify_email(self):
        mongo.user_collection.update_one(
            {"username": self.username},
            {"$set": {"is_verified": True}, "$unset": {"verification_code": 1}},
        )

    def reset_password(self, new_password):
        hashed_password = get_password_hash(new_password)
        mongo.user_collection.update_one(
            {"username": self.username},
            {
                "$set": {"hashed_password": hashed_password},
                "$unset": {"reset_token": 1},
            },
        )

    def to_dict(self):
        return {
            "username": self.username,
            "email": self.email,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "phone_number": self.phone_number,
            "dob": self.dob,
            "country": self.country,
            "is_verified": self.is_verified,
        }
