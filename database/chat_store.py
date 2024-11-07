from datetime import datetime
from typing import List, Optional, Dict
from pymongo import MongoClient
from bson import ObjectId
from config import settings  # Import the config module

class ChatMessage:
    def __init__(self, msg: str, msg_id: Optional[str] = None, created_at: Optional[datetime] = None, feedback: Optional[str] = None):
        self.id = msg_id or str(ObjectId())
        self.msg = msg
        self.created_at = created_at or datetime.utcnow()
        self.feedback = feedback

    def to_dict(self) -> Dict:
        data = {
            "id": self.id,
            "msg": self.msg,
            "created_at": self.created_at
        }
        if self.feedback is not None:
            data["feedback"] = self.feedback
        return data

    @classmethod
    def from_dict(cls, data: Dict) -> "ChatMessage":
        return cls(
            msg=data["msg"],
            msg_id=data["id"],
            created_at=data["created_at"],
            feedback=data.get("feedback")
        )

class ChatSession:
    def __init__(self, user_id: str, messages: Optional[List[ChatMessage]] = None, 
                 session_id: Optional[str] = None, created_at: Optional[datetime] = None):
        self.id = session_id or str(ObjectId())
        self.user_id = user_id
        self.messages = messages or []
        self.created_at = created_at or datetime.utcnow()
        self.last_interaction_at = self.created_at

    def to_dict(self) -> Dict:
        return {
            "_id": ObjectId(self.id),
            "user_id": self.user_id,
            "messages": [msg.to_dict() for msg in self.messages],
            "created_at": self.created_at,
            "last_interaction_at": self.last_interaction_at
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "ChatSession":
        messages = [ChatMessage.from_dict(msg) for msg in data["messages"]]
        session = cls(
            user_id=data["user_id"],
            messages=messages,
            session_id=str(data["_id"]),
            created_at=data["created_at"]
        )
        session.last_interaction_at = data["last_interaction_at"]
        return session

class ChatStore:
    def __init__(self):
        self.client = MongoClient(settings.MONGODB_URL)
        self.db = self.client[settings.MONGO_DATABASE]
        self.chat_sessions = self.db.chat_sessions

    def create_session(self, user_id: str) -> ChatSession:
        session = ChatSession(user_id=user_id)
        self.chat_sessions.insert_one(session.to_dict())
        return session

    def get_session(self, session_id: str) -> Optional[ChatSession]:
        session_data = self.chat_sessions.find_one({"_id": ObjectId(session_id)})
        return ChatSession.from_dict(session_data) if session_data else None

    def update_session_messages(self, session_id: str, new_messages: List[ChatMessage]) -> bool:
        """
        Update a chat session with new messages while preserving existing ones
        """
        session = self.get_session(session_id)
        if not session:
            return False

        # Add new messages to existing ones
        session.messages.extend(new_messages)
        session.last_interaction_at = datetime.utcnow()

        # Update in database
        result = self.chat_sessions.update_one(
            {"_id": ObjectId(session_id)},
            {
                "$set": {
                    "messages": [msg.to_dict() for msg in session.messages],
                    "last_interaction_at": session.last_interaction_at
                }
            }
        )
        return result.modified_count > 0

    def get_user_sessions(self, user_id: str, limit: int = 10) -> List[ChatSession]:
        """
        Get user's chat sessions, sorted by last interaction (most recent first)
        """
        sessions_data = self.chat_sessions.find(
            {"user_id": user_id}
        ).sort("last_interaction_at", -1).limit(limit)
        
        return [ChatSession.from_dict(session) for session in sessions_data]

    def update_message_feedback(self, session_id: str, message_id: str, feedback: str) -> bool:
        """
        Update feedback string for a specific message in a session
        """
        result = self.chat_sessions.update_one(
            {
                "_id": ObjectId(session_id),
                "messages.id": message_id
            },
            {
                "$set": {
                    "messages.$.feedback": feedback
                }
            }
        )
        return result.modified_count > 0
