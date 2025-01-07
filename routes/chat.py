from utils.jwt import JWT
from fastapi import APIRouter, Header
from config import settings
from utils.logger import setup_logger
from utils.helper import document_to_promptable
from pydantic import BaseModel
from typing import Optional
import uuid

from services.session import SessionService
from services.document import DocumentService
from services.redis import RedisService
from services.xai import XAICompletion
from services.xai import XAIEmbedding
from services.pinecone import PineconeService

jwt = JWT(settings.JWT_SECRET_KEY, "HS256")
session_service = SessionService()
redis_service = RedisService()
document_service = DocumentService()
xai_service = XAICompletion()
embed = XAIEmbedding()
pinecone_service = PineconeService()

chat_router = APIRouter()
logger = setup_logger('chat')

class ChatRequest(BaseModel):
    message: str
    document_id: Optional[str] = None
    context_type: str = "both"

@chat_router.post("/kv-chat")
async def chat(
    request: ChatRequest,
    authorization: str = Header(...),
    session_id: Optional[str] = Header(None),
):  
    try:
        user_id = jwt.decode_token(authorization)["sub"]
        is_new_session = False
        if not session_id:
            session_id = str(uuid.uuid4())
            is_new_session = True
            session_service.create_session(user_id, session_id, type='chat')
        
        conversation = redis_service.get_conversation(session_id)
        kb_mongo_result = ""
        kb_pinecone_result = ""
        intent_response = xai_service.analyze_intent(conversation, request.message)
        intent = intent_response.get('intent')

        if intent == 'out_of_scope':
            return {
                "response": "I'm sorry, I don't understand that. Please ask me about lending or loan options.",
                "session_id": session_id,
                "intent": intent,
                "intent_confidence": intent_response.get('confidence'),
                "intent_reason": intent_response.get('reason')
            }

        if intent in ["follow_up_lender", "filtered_lender"]:
            query = xai_service.query_from_chat(request.message, conversation)
            kb_mongo_result = document_service.search_documents(query)
            kb_mongo_result = document_to_promptable(kb_mongo_result)

            vector = embed.create_embedding(request.message)
            kb_pinecone_result = pinecone_service.query_vectors(vector)
            
            print(f"Pinecone result: {kb_pinecone_result}") 

        if kb_mongo_result == "" and kb_pinecone_result == "":
            return {
                "response": "I'm sorry, I couldn't find any information. Please try again.",
                "session_id": session_id,
                "intent": intent,
                "intent_confidence": intent_response.get('confidence'),
                "intent_reason": intent_response.get('reason')
            }
        
        response = xai_service.generate_response(intent, request.message, conversation, kb_mongo_result, kb_pinecone_result)

        if response is None:
            return {
                "response": "I'm sorry, I couldn't generate a response. Please try again.",
                "session_id": session_id,
                "intent": intent,
                "intent_confidence": intent_response.get('confidence'),
                "intent_reason": intent_response.get('reason')
            }

        new_conversation = [
            {"role": "user", "content": request.message},
            {"role": "assistant", "content": response.get('response')}
        ]

        conversation.extend(new_conversation)
        redis_service.save_conversation(session_id, conversation)
        session_service.update_session_messages(session_id, conversation, title=response.get('chat_title'))

        return {
            "response": response.get('response'),
            "session_id": session_id,
            "intent": intent,
            "intent_confidence": intent_response.get('confidence'),
            "intent_reason": intent_response.get('reason')
        }
    
    except Exception as e:
        logger.error(f"Error while generating response : {str(e)}")
        return {"response": "I'm sorry, I'm having trouble understanding you right now. Please try again later."}