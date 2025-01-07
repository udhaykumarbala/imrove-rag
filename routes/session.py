from utils.jwt import JWT
from fastapi import APIRouter, Header
from fastapi import Header, Form
from config import settings
from utils.logger import setup_logger

from services.session import SessionService
from services.redis import RedisService

jwt = JWT(settings.JWT_SECRET_KEY, "HS256")
session_service = SessionService()
redis_service = RedisService()

session_router = APIRouter()
logger = setup_logger('session')

# Get user sessions endpoint
@session_router.get("/sessions")
async def get_sessions(authorization: str = Header(...), limit: int = 10):
    user_id = jwt.decode_token(authorization)["sub"]
    return session_service.get_user_sessions(user_id, limit)

# Get session details endpoint
@session_router.get("/session")
async def get_session(authorization: str = Header(...), session_id: str = Header(...)):
    user_id = jwt.decode_token(authorization)["sub"]
    session = session_service.get_session(user_id, session_id)
    session_messages = [message.to_dict() for message in session.messages]
    redis_service.save_session(session_id, session_messages)
    if session.type == "upload":
        redis_service.save_document_info(session_id, session.document_info)
    return session

# Update message feedback endpoint
@session_router.post("/update_message_feedback")
async def update_message_feedback(authorization: str = Header(...), session_id: str = Header(...), message_index: int = Form(...), feedback: str = Form(...), rating: int = Form(...)):
    user_id = jwt.decode_token(authorization)["sub"]
    return session_service.update_message_feedback(user_id, session_id, message_index, feedback, rating)

# Update the title of the session
@session_router.post("/update_session_title")
async def update_session_title(authorization: str = Header(...), session_id: str = Header(...), title: str = Form(...)):
    user_id = jwt.decode_token(authorization)["sub"]
    return session_service.update_session_title(user_id, session_id, title)