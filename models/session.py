from datetime import datetime
from typing import List, Optional, Dict
from pymongo import MongoClient
from bson import ObjectId
from config import settings

class ChatMessage:
    def __init__(self, role: str, content: str, feedback: Optional[str] = None, rating: Optional[int] = None):
        self.role = role
        self.content = content
        self.feedback = feedback
        self.rating = rating

    def to_dict(self):
        return {
            "role": self.role,
            "content": self.content,
            "feedback": self.feedback,
            "rating": self.rating
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            role=data["role"],
            content=data["content"],
            feedback=data.get("feedback"),
            rating=data.get("rating")
        )

class ChatSession:
    def __init__(self, id: str, session_id: str, user_id: str, type: str, messages: List[ChatMessage], 
                 document_id: Optional[str] = None, document_info: Optional[dict] = None,
                 created_at: Optional[datetime] = None, last_interaction_at: Optional[datetime] = None, title: str = "new chat"):
        self.id = id
        self.session_id = session_id
        self.user_id = user_id
        self.type = type
        self.messages = messages
        self.document_id = document_id
        self.document_info = document_info
        self.created_at = created_at or datetime.now()
        self.last_interaction_at = last_interaction_at or self.created_at
        self.title = title

    def to_dict(self):
        return {
            "_id": self.id,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "type": self.type,
            "messages": [msg.to_dict() for msg in self.messages],
            "document_id": self.document_id,
            "document_info": self.document_info,
            "created_at": self.created_at.timestamp(),
            "last_interaction_at": self.last_interaction_at.timestamp(),
            "title": self.title
        }

    @classmethod
    def from_dict(cls, data):
        messages = [ChatMessage.from_dict(msg) for msg in data.get("messages", [])]
        
        created_at = cls._parse_datetime(data.get("created_at"))
        last_interaction_at = cls._parse_datetime(data.get("last_interaction_at"), default=created_at)

        return cls(
            id=str(data.get("_id", data.get("id"))),
            session_id=data.get("session_id"),
            user_id=data["user_id"],
            type=data.get("type", "chat"),
            messages=messages,
            document_id=data.get("document_id"),
            document_info=data.get("document_info"),
            created_at=created_at,
            last_interaction_at=last_interaction_at,
            title=data.get("title", "new chat")
        )

    @staticmethod
    def _parse_datetime(value, default=None):
        if isinstance(value, str):
            return datetime.fromisoformat(value)
        if isinstance(value, datetime):
            return value
        return default