import redis
from config import settings
import os
from typing import Optional

class Redis:
    _instance = None
    _client: Optional[redis.Redis] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Redis, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._client:
            self.host = settings.REDIS_HOST
            self.port = settings.REDIS_PORT
            self.password = settings.REDIS_PASSWORD

    def connect(self):
        """
        Connect to Redis and return client
        Returns:
            Redis: Redis client instance
        """
        try:
            if not self._client:
                self._client = redis.Redis(
                    host=self.host,
                    port=self.port,
                    password=self.password,
                    decode_responses=True
                )
                # Test the connection
                self._client.ping()
                print("Successfully connected to Redis!")
            return self._client
        except redis.ConnectionError as e:
            print(f"Error connecting to Redis: {e}")
            raise

    def close(self):
        """Close Redis connection"""
        if self._client:
            self._client.close()
            self._client = None
