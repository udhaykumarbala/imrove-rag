from pymongo import MongoClient
from config import settings
import os
from typing import Optional

class MongoDB:
    _instance = None
    _client: Optional[MongoClient] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MongoDB, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._client:
            self.uri = settings.MONGODB_URL
            self.database_name = settings.MONGO_DATABASE
            
    def connect(self):
        try:
            if not self._client:
                self._client = MongoClient(self.uri)
                # Test the connection
                self._client.admin.command('ping')
                print("Successfully connected to MongoDB!")
            return self._client[self.database_name]
        except Exception as e:
            print(f"Error connecting to MongoDB: {e}")
            raise

    def close(self):
        if self._client:
            self._client.close()
            self._client = None
            
    def get_collection(self, collection_name: str):
        """
        Get a MongoDB collection by name
        Args:
            collection_name (str): Name of the collection
        Returns:
            Collection: MongoDB collection object
        """
        db = self.connect()
        return db[collection_name]
