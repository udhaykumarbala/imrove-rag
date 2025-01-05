from datetime import datetime
from typing import Dict, List, Optional
from bson import ObjectId
from databases.mongo import MongoDB
from models.session import ChatMessage, ChatSession

class SessionService:
    def __init__(self):
        self.client = MongoDB().connect()
        self.chat_sessions = self.client.get_collection('chat_sessions')

    def create_session(self, user_id: str, session_id: str, type: str = 'chat', document_id: Optional[str] = None, document_info: Optional[Dict] = None) -> ChatSession:
        session = ChatSession(
            id=str(ObjectId()),
            session_id=session_id,
            user_id=user_id,
            type=type,
            messages=[],
            title="new chat",
            document_id=document_id,
            document_info=document_info,
            created_at=datetime.utcnow()
        )
        self.chat_sessions.insert_one(session.to_dict())
        return session

    def get_session(self, user_id: str, session_id: str) -> Optional[ChatSession]:
        session_data = self.chat_sessions.find_one({"session_id": session_id, "user_id": user_id})
        return ChatSession.from_dict(session_data) if session_data else None

    def get_session_by_document_id(self, user_id: str, document_id: str) -> Optional[ChatSession]:
        session_data = self.chat_sessions.find_one({"document_id": document_id, "user_id": user_id})
        return ChatSession.from_dict(session_data) if session_data else None

    def update_session_messages(self, session_id: str, all_messages: List[ChatMessage], title: str) -> bool:
        last_interaction_at = datetime.utcnow()

        update_fields = {
            "messages": [msg if isinstance(msg, dict) else msg.to_dict() for msg in all_messages],
            "last_interaction_at": last_interaction_at
        }

        if title:
            update_fields["title"] = title

        result = self.chat_sessions.update_one(
            {"session_id": session_id},
            {"$set": update_fields}
        )
        return result.modified_count > 0

    def update_session_document_info(self, session_id: str, document_info: Dict) -> bool:
        result = self.chat_sessions.update_one(
            {"session_id": session_id},
            {"$set": {"document_info": document_info}}
        )
        return result.modified_count > 0

    def get_user_sessions(self, user_id: str, limit: int = 25) -> List[Dict]:
        sessions_data = self.chat_sessions.find(
            {"user_id": user_id}
        ).sort("last_interaction_at", -1).limit(limit)
        
        return [
            {
                "id": str(session['_id']),
                "session_id": session['session_id'],
                "title": session['title'],
                "type": session['type'],
                "last_interaction_at": session['last_interaction_at']
            }
            for session in sessions_data
        ]

    def update_message_feedback(self, user_id: str, session_id: str, message_index: int, feedback: str, rating: int) -> bool:
        result = self.chat_sessions.update_one(
            {
                "session_id": session_id,
                "user_id": user_id
            },
            {
                "$set": {
                    f"messages.{message_index}.feedback": feedback,
                    f"messages.{message_index}.rating": rating
                }
            }
        )
        return result.modified_count > 0

    def update_session_title(self, user_id: str, session_id: str, title: str) -> bool:
        result = self.chat_sessions.update_one(
            {"session_id": session_id, "user_id": user_id},
            {"$set": {"title": title}}
        )
        return result.modified_count > 0