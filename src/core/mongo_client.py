import pymongo
from pymongo.errors import ServerSelectionTimeoutError

from src.secrets import secrets


class MongoConnect:
    def __init__(self):
        self.db = pymongo.MongoClient(secrets["mongodb_conn_string"])
        self.db_connect()

    def db_connect(self):
        try:
            db = self.db[secrets["db_name"]]
            self.user_collection = db[secrets["user_collection"]]
            self.social_auth_collection = db[secrets["social_auth_collection"]]
            self.email_analysis_collection = db[secrets["email_analysis_collection"]]
            self.raw_emails = db[secrets["raw_emails"]]
            self.processed_emails = db[secrets["processed_emails"]]
        except ServerSelectionTimeoutError:
            pass

    async def close(self):
        if self.user_collection:
            self.user_collection.close()
        if self.social_auth_collection:
            self.social_auth_collection.close()
        if self.email_analysis_collection:
            self.email_analysis_collection.close()
        if self.raw_emails:
            self.raw_emails.close()
        if self.processed_emails:
            self.processed_emails.close()


mongo = MongoConnect()
