from utils.jwt import JWT
from typing import List, Optional
from pydantic import BaseModel
import mimetypes
import os
import uuid 
from fastapi import APIRouter, UploadFile, File, Header, HTTPException, Depends
from config import settings
from utils.logger import setup_logger

from services.document import DocumentService
from services.processor import DocumentProcessor
from services.session import SessionService
from services.redis import RedisService
from services.xai import XAICompletion
from services.embedding import *

from models.document import LoanDocument

ALLOWED_MIMETYPES = {
    'application/pdf': '.pdf',
    'image/jpeg': '.jpg',
    'image/png': '.png',
    'application/msword': '.doc',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx',
    'text/plain': '.txt'
}

jwt = JWT(settings.JWT_SECRET_KEY, "HS256")
processor = DocumentProcessor()
document_service = DocumentService()
session_service = SessionService()
redis_service = RedisService()
xai_service = XAICompletion()
pinecone_service = PineconeService()   

upload_router = APIRouter()
logger = setup_logger('upload')

class ChatRequest(BaseModel):
    message: str
    document_id: Optional[str] = None
    context_type: str = "both"

async def get_user_id(authorization):
    user_id = jwt.decode_token(authorization)["sub"]
    return user_id

@upload_router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    authorization: str = Header(...),
    session_id: Optional[str] = Header(None)
):  
    user_id = await get_user_id(authorization)
    logger.info(f"File upload request - User: {user_id}, "f"File: {file.filename}, Session: {session_id}")

    if not session_id:
        session_id = str(uuid.uuid4())

    content_type = file.content_type
    if content_type not in ALLOWED_MIMETYPES:
        raise HTTPException(status_code=400, detail=f"File type not allowed. Allowed types: {', '.join(ALLOWED_MIMETYPES.values())}")

    try:
        # Processing document
        content = await file.read()
        text = processor.process_document(content, file.filename)
        if not text:
            logger.info(f"Failed to extract text from document - User: {user_id}, "f"File: {file.filename}")
            return {
                "session_id": session_id,
                "message": "Failed to extract text from document"
            }

        document_id = str(uuid.uuid4())

        # Check document relevance
        relevancy = xai_service.check_relevance(text)
        if relevancy.get('document_type') == 'irrelevant_document':
            return {
                "session_id": session_id,
                "message": "The document is not relevant",
                "confidence": relevancy.confidence
            }

        # Extract document information
        document_info = xai_service.ingest_document(text)
        print(document_info)
        extracted_info = document_info.get('extracted_info')

        # Check if document already exists based on company name
        similar_documents = document_service.find_similar_documents(LoanDocument(**extracted_info))
        
        print(similar_documents)

        # Check if the user has an existing session with all similar documents
        existing_session = None
        for document_data in similar_documents:
            document = LoanDocument.from_dict(document_data)
            existing_session = session_service.get_session_by_document_id(user_id, document.document_id)
            if not existing_session:
                break
        
        # If similar document exists and user has no existing session
        if len(similar_documents) and not existing_session:
            conversation = [
                {"role": "user", "content": "Uploaded document"},
                {"role": "assistant", "content": "Similar document already exists. Contact admin for more information."}
            ]
            redis_service.save_conversation(session_id, conversation)
            session_service.create_session(user_id, session_id, type='upload', document_id=document_id, document_info=extracted_info)
            session_service.update_session_messages(session_id, conversation, title=document_info.get('chat_title'))
            return {
                "session_id": session_id,
                "message": "Similar document already exists. Contact admin for more information.",
            }

        # If similar document exists and user has existing session, redirect to existing session
        if existing_session:
            conversation = [
                {"role": "user", "content": "Uploaded document"},
                {"role": "assistant", "content": "Similar document already exists."}
            ]
            redis_service.save_conversation(session_id, conversation)
            session_service.create_session(user_id, session_id, type='upload', document_id=document_id, document_info=extracted_info)
            session_service.update_session_messages(session_id, conversation, title=document_info.get('chat_title'))
            logger.info(f"Similar document already exists - User: {user_id}, "f"Document ID: {document_id}")
            return {
                "session_id": existing_session.session_id,
                "document_id": existing_session.document_id,
                "message": "Similar document already exists."
            }

        # Storing document information in Redis
        redis_service.save_previous_info(session_id, extracted_info)
        redis_service.save_document_id(session_id, document_id)

        conversation = [
            {"role": "user", "content": "Uploaded document"},
            {"role": "assistant", "content": document_info.get('message')}
        ]
        redis_service.save_conversation(session_id, conversation)

        # Storing session information in MongoDB
        session_service.create_session(user_id, session_id, type='upload', document_id=document_id, document_info=extracted_info)
        session_service.update_session_messages(session_id, conversation, title=document_info.get('chat_title'))

        logger.info(f"File processed successfully - User: {user_id}, "f"Document ID: {document_id}")
        return {
            "session_id": session_id,
            "document_id": document_id,
            "extracted_info": extracted_info,
            "message": document_info.get('message')
        }

    except Exception as e:
        logger.error(f"Upload failed - User: {user_id}, Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@upload_router.post("/upload_chat")
async def chat_with_document(
    request: ChatRequest, 
    authorization: str = Header(...),
    session_id: str = Header(...)
):
    user_id = await get_user_id(authorization)
    logger.info(f"Chat request - User: {user_id}, "f"Session: {session_id}")

    try:
        conversation = redis_service.get_conversation(session_id)
        previous_info = redis_service.get_previous_info(session_id)
        document_id = redis_service.get_document_id(session_id)

        response = xai_service.chat_with_document(user_message=request.message, conversation=conversation, document_info=previous_info)

        if response.get("consent"):
            try: 
                response_data = response
                if not document_service.get_document_by_id(document_id):
                    loan_document = LoanDocument(document_id=document_id, created_by=user_id, **response_data['extracted_info'])
                    document_service.store_document(loan_document)
                else:
                    loan_document = LoanDocument(document_id=document_id, created_by=user_id, **response_data['extracted_info'])
                    loan_document_dict = loan_document.to_dict()
                    if '_id' in loan_document_dict:
                        del loan_document_dict['_id']
                    document_service.update_document(document_id, loan_document_dict)

                upsert_embedding(document_id, user_id, response_data['extracted_info'])
                logger.info(f"Document upload completed - User: {user_id}, "f"Document: {document_id}")

            except Exception as e:
                logger.error(f"Error uploading document: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        conversation.extend([
            {"role": "user", "content": request.message},
            {"role": "assistant", "content": response.get('message')}
        ])

        # Save conversation in Redis
        redis_service.save_conversation(session_id, conversation)
        session_service.update_session_messages(session_id, conversation, "")

        # Save extracted info in Redis and MongoDB
        if response.get('extracted_info'):
            redis_service.save_previous_info(session_id, response.get('extracted_info'))
            session_service.update_session_document_info(session_id, response.get('extracted_info'))

        return {
            "extracted_info": response.get('extracted_info') if response.get('extracted_info') else None,
            "message": response.get('message'),
            "session_id": session_id
        }
                
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
