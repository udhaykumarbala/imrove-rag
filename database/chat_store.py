from datetime import datetime
from typing import List, Optional, Dict
from pymongo import MongoClient
from bson import ObjectId
from config import settings  # Import the config module

class ChatMessage:
    def __init__(self, role: str, content: str, feedback: Optional[str] = None):
        self.role = role
        self.content = content
        self.feedback = feedback

    def to_dict(self):
        return {
            "role": self.role,
            "content": self.content,
            "feedback": self.feedback
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            role=data["role"],
            content=data["content"],
            feedback=data.get("feedback", None)
        )

class ChatSession:
    def __init__(self, id: str, session_id: str, user_id: str, type: str, messages: List[ChatMessage], 
                 document_id: Optional[str] = None, document_info: Optional[dict] = None,
                 created_at: Optional[datetime] = None, last_interaction_at: Optional[datetime] = None):
        self.id = id
        self.session_id = session_id
        self.user_id = user_id
        self.type = type
        self.messages = messages
        self.document_id = document_id
        self.document_info = document_info
        self.created_at = created_at or datetime.now()
        self.last_interaction_at = last_interaction_at or self.created_at
        self.title = f"session_{session_id}"

    def to_dict(self):
        return {
            "_id": self.id,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "type": self.type,
            "messages": [msg.to_dict() for msg in self.messages],
            "document_id": self.document_id,
            "document_info": self.document_info,
            "created_at": self.created_at.isoformat(),
            "last_interaction_at": self.last_interaction_at.isoformat(),
            "title": self.title
        }

    @classmethod
    def from_dict(cls, data):
        messages = [ChatMessage.from_dict(msg) for msg in data.get("messages", [])]
        
        # Handle created_at that could be datetime or string
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        elif isinstance(created_at, datetime):
            created_at = created_at
        else:
            created_at = None

        # Handle last_interaction_at that could be datetime or string
        last_interaction_at = data.get("last_interaction_at")
        if isinstance(last_interaction_at, str):
            last_interaction_at = datetime.fromisoformat(last_interaction_at)
        elif isinstance(last_interaction_at, datetime):
            last_interaction_at = last_interaction_at
        else:
            last_interaction_at = created_at  # Default to created_at if not present

        session = cls(
            id=str(data.get("_id", data.get("id"))),
            session_id=data.get("session_id"),
            user_id=data["user_id"],
            type=data.get("type", "chat"),
            messages=messages,
            document_id=data.get("document_id"),
            document_info=data.get("document_info"),
            created_at=created_at,
            last_interaction_at=last_interaction_at
        )
        session.title = data.get("title", f"session_{session.id}")
        return session

class ChatStore:
    def __init__(self):
        self.client = MongoClient(settings.MONGODB_URL)
        self.db = self.client[settings.MONGO_DATABASE]
        self.chat_sessions = self.db.chat_sessions

    def create_session(self, user_id: str, session_id: str, type: str = 'chat', document_id: Optional[str] = None, document_info: Optional[Dict] = None) -> ChatSession:
        session = ChatSession(
            id=str(ObjectId()),
            session_id=session_id,
            user_id=user_id,
            type=type,
            messages=[],
            document_id=document_id,
            document_info=document_info,
            created_at=datetime.utcnow()
        )
        self.chat_sessions.insert_one(session.to_dict())
        return session

    def get_session(self, user_id: str, session_id: str) -> Optional[ChatSession]:
        session_data = self.chat_sessions.find_one({"session_id": session_id, "user_id": user_id})
        return ChatSession.from_dict(session_data) if session_data else None

    def update_session_messages(self, session_id: str, all_messages: List[ChatMessage]) -> bool:
        """
        Update a chat session with new messages while preserving existing ones
        """
        last_interaction_at = datetime.utcnow()

        # Update in database
        result = self.chat_sessions.update_one(
            {"session_id": session_id},
            {
                "$set": {
                    "messages": all_messages,
                    "last_interaction_at": last_interaction_at
                }
            }
        )
        return result.modified_count > 0

    def update_session_document_info(self, session_id: str, document_info: Dict) -> bool:
        result = self.chat_sessions.update_one(
            {"session_id": session_id},
            {"$set": {"document_info": document_info}}
        )
        return result.modified_count > 0

    def get_user_sessions(self, user_id: str, limit: int = 10) -> List[ChatSession]:
        """
        Get user's chat sessions, sorted by last interaction (most recent first)
        """
        sessions_data = self.chat_sessions.find(
            {"user_id": user_id}
        ).sort("last_interaction_at", -1).limit(limit)
        
        sessions = []
        for session in sessions_data:
            session['_id'] = str(session['_id'])
            sessions.append(ChatSession.from_dict(session))
        
        return sessions

    def update_message_feedback(self, user_id: str, session_id: str, message_index: int, feedback: str) -> bool:
        """
        Update feedback string for a specific feedback in a message with index
        """
        result = self.chat_sessions.update_one(
            {
                "session_id": session_id,
                "user_id": user_id
            },
            {
                "$set": {
                    f"messages.{message_index}.feedback": feedback
                }
            }
        )
        return result.modified_count > 0
