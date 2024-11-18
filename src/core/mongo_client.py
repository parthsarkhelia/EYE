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
            self.base_collection = db[secrets["base_collection"]]
            self.social_auth_collection = db[secrets["social_auth_collection"]]
        except ServerSelectionTimeoutError:
            pass

    async def close(self):
        if self.base_collection:
            self.base_collection.close()
        if self.social_auth_collection:
            self.social_auth_collection.close()


mongo = MongoConnect()
