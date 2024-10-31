import redis
import json
from typing import List, Dict

class RedisHandler:
    def __init__(self, host: str, port: int, password: str = None):
        self.redis_client = redis.Redis(
            host=host,
            port=port,
            password=password,
            decode_responses=True
        )
    
    def save_conversation(self, session_id: str, messages: List[Dict[str, str]]):
        self.redis_client.setex(
            f"conversation:{session_id}",
            3600,  # 1 hour expiry
            json.dumps(messages)
        )
    
    def get_conversation(self, session_id: str) -> List[Dict[str, str]]:
        conversation = self.redis_client.get(f"conversation:{session_id}")
        return json.loads(conversation) if conversation else []
    
    def save_previous_info(self, session_id: str, previous_info: Dict[str, str]):
        self.redis_client.setex(
            f"previous_info:{session_id}",
            3600,  # 1 hour expiry
            json.dumps(previous_info)
        )

    def get_previous_info(self, session_id: str) -> Dict[str, str]:
        previous_info = self.redis_client.get(f"previous_info:{session_id}")
        return json.loads(previous_info) if previous_info else {}
    
    def save_document_id(self, session_id: str, document_id: str):
        print(f"document_id: {document_id} is saved in redis")
        print(f"session_id: {session_id} is saved in redis")
        self.redis_client.setex(
            f"document_id:{session_id}",
            3600,  # 1 hour expiry
            document_id
        )

    def get_document_id(self, session_id: str) -> str:
        document_id = self.redis_client.get(f"document_id:{session_id}")
        return document_id if document_id else None