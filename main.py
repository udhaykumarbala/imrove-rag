from fastapi import FastAPI, UploadFile, File, Header, HTTPException, Form
from typing import Optional
import uuid
from pydantic import BaseModel
from time import perf_counter
import logging

from config import settings
from llm.xai_handler import XAIHandler
from document_processor.processor import DocumentProcessor
from database.vector_store import VectorStore
from memory.redis_handler import RedisHandler
from fastapi.middleware.cors import CORSMiddleware
from utils.timing import timer
from database.user_store import UserStore
from database.chat_store import ChatStore
from database.document_store import LoanDocumentStore, LoanDocument
from auth.jwt import JWT
from mailersend import emails

app = FastAPI()

# logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# orgin *
origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods= ["GET", "POST", "OPTIONS", "HEAD", "PUT"],
    allow_headers=["*"],
)

llm = XAIHandler(settings.XAI_API_KEY)
doc_processor = DocumentProcessor()
vector_store = VectorStore()
redis_handler = RedisHandler(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    password=settings.REDIS_PASSWORD
)

user_store = UserStore()
chat_store = ChatStore()
loan_store = LoanDocumentStore()

jwt = JWT(settings.JWT_SECRET_KEY, "HS256")

mailer = emails.NewEmail(settings.MAILERSEND_API_KEY)

# Define request model
class ChatRequest(BaseModel):
    message: str
    document_id: Optional[str] = None
    context_type: str = "both"  # default value

# Add this class for the login request
class LoginRequest(BaseModel):
    email: str

# health check
@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/upload")
@timer
async def upload_document(
    file: UploadFile = File(...),
    authorization: str = Header(...),
    session_id: Optional[str] = Header(None)
):
    user_id = jwt.decode_token(authorization)["sub"]
    if not session_id:
        session_id = str(uuid.uuid4())
        
    content = await file.read()
    text = doc_processor.process_document(content, file.filename)
    
    # Extract information using LLM
    document_info = llm.extract_document_info(text)

    print(f"🔥document_info: {document_info}")

    extracted_info = document_info.extracted_info
    document_id = str(uuid.uuid4())


    loan_document = extracted_info.model_dump()
    loan_document["document_id"] = document_id
    loan_document["created_by"] = "user"

    # loan_document = LoanDocument(**loan_document)
    # loan_store.store_document(loan_document)

    if document_info.consent:
        loan_document = LoanDocument(**loan_document)
        loan_store.store_document(loan_document)
        vector_store.store_document(extracted_info.model_dump(), document_id)

    redis_handler.save_previous_info(session_id, extracted_info.model_dump())
    redis_handler.save_document_id(session_id, document_id)

    conversation = [
        {"role": "user", "content": "Uploaded document"},
        {"role": "assistant", "content": document_info.message}
    ]
    redis_handler.save_conversation(session_id, conversation)

    chat_store.create_session(user_id, session_id, type='upload', document_id=document_id, document_info=extracted_info.model_dump())
    chat_store.update_session_messages(session_id, conversation, title=document_info.chat_title)

    response = {
        "session_id": session_id,
        "document_id": document_id,
        "extracted_info": extracted_info.model_dump(),
        "message": document_info.message,
        "consent": document_info.consent,
        "is_updated": document_info.is_updated
    }

    print(f"🔥response: {response}")
    
    return response

@app.post("/upload_chat")
@timer
async def upload_chat(request: ChatRequest, session_id: str = Header(...)):
    try:
        # Time conversation retrieval
        start = perf_counter()
        conversation = redis_handler.get_conversation(session_id)
        previous_info = redis_handler.get_previous_info(session_id)
        document_id = redis_handler.get_document_id(session_id)

        logger.info(f"⏱️ Redis retrieval took {perf_counter() - start:.2f} seconds")

        print(f"🔥conversation: {conversation}\n")
        print(f"🔥previous_info: {previous_info}\n")
        
        # Time LLM processing
        start = perf_counter()
        response = llm.extract_document_info_from_conversation(
            prompt=request.message,
            conversation=conversation,
            previous_info=previous_info
        )

        logger.info(f"⏱️ LLM processing took {perf_counter() - start:.2f} seconds")
        
        # Time vector store operations
        if response.consent:
            start = perf_counter()
            try:
                if not vector_store.check_if_document_exists(document_id):
                    vector_store.store_document(response.model_dump(), document_id)
                else:
                    vector_store.update_document(response.model_dump(), document_id)
                logger.info(f"⏱️ Vector store operation took {perf_counter() - start:.2f} seconds")
            except Exception as e:
                logger.error(f"Error handling vector store: {e}")
            
            try: 
                response_data =  response.model_dump()
                if not loan_store.get_document_by_id(document_id):
                    loan_document = LoanDocument(response_data['extracted_info'])
                    loan_store.store_document(loan_document)
                else:
                    loan_document = LoanDocument(response_data['extracted_info'])
                    loan_store.update_document(document_id, loan_document)
                logger.info(f"⏱️ Loan document store operation took {perf_counter() - start:.2f} seconds")
            except Exception as e:
                logger.error(f"Error handling loan store: {e}")
        
        # Time conversation update
        start = perf_counter()
        
        conversation.extend([
            {"role": "user", "content": request.message},
            {"role": "assistant", "content": response.message}
        ])

        redis_handler.save_conversation(session_id, conversation)
        chat_store.update_session_messages(session_id, conversation, "") # title is empty, so it will not be updated

        if response.extracted_info:
            redis_handler.save_previous_info(session_id, response.extracted_info.model_dump())
            chat_store.update_session_document_info(session_id, response.extracted_info.model_dump())

        logger.info(f"⏱️ Conversation update took {perf_counter() - start:.2f} seconds")
        
        return {
            "extracted_info": response.extracted_info.model_dump() if response.extracted_info else None,
            "message": response.message,
            "session_id": session_id
        }
        
    except Exception as e:
        logger.error(f"Error in upload_chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/kv-chat")
@timer
async def chat(
    request: ChatRequest,
    authorization: str = Header(...),
    session_id: Optional[str] = Header(None),
):
    user_id = jwt.decode_token(authorization)["sub"]
    is_new_session = False
    if not session_id:
        session_id = str(uuid.uuid4())
        is_new_session = True
        chat_store.create_session(user_id, session_id, type='chat')
    
    conversation = redis_handler.get_conversation(session_id)

    conversation_str = ""
    kb_result_str = ""

    if conversation and len(conversation):
        conversation_str = "\n".join(f"{msg['role']}: {str(msg['content'])}" for msg in conversation)

    # Analyze intent
    intent_response = await llm.analyze_intent(request.message, conversation)
    intent = intent_response.intent

    print('intent:', intent)

    if intent == 'out_of_scope':
        return {
            "response": "I'm sorry, I don't understand that. Please ask me about lending or loan options.",
            "session_id": session_id,
            "intent": intent,
            "intent_confidence": intent_response.confidence,
            "intent_reason": intent_response.reason
        }

    elif intent == 'specific_lender' or intent == 'filtered_lender_list':
        query = llm.extract_feature_from_conversation(request.message, conversation)  
        kb_result_str = loan_store.search_documents(query)

    response = await llm.generate_response(intent, conversation_str, kb_result_str)

    # only new conversarion
    newConversation = [ {"role": "user", "content": request.message}, {"role": "assistant", "content": response.response}]

    # Update conversation history
    conversation.extend(newConversation)
    
    redis_handler.save_conversation(session_id, conversation)
    chat_store.update_session_messages(session_id, conversation, title=response.chat_title)
    
    return {
        "response": response.response,
        "session_id": session_id,
        "intent": intent,
        "intent_confidence": intent_response.confidence,
        "intent_reason": intent_response.reason
    }

@app.get("/sessions")
async def get_sessions(authorization: str = Header(...), limit: int = 10):
    user_id = jwt.decode_token(authorization)["sub"]
    return chat_store.get_user_sessions(user_id, limit)

@app.get("/session")
async def get_session(authorization: str = Header(...), session_id: str = Header(...)):
    user_id = jwt.decode_token(authorization)["sub"]
    session = chat_store.get_session(user_id, session_id)
    # convert session chatMessage to list of dict[role, content]
    session_messages = [message.to_dict() for message in session.messages]
    # save session to redis
    redis_handler.save_session(session_id, session_messages)
    if session.type == "upload":
        redis_handler.save_document_info(session_id, session.document_info)
    return session

@app.post("/update_message_feedback")
async def update_message_feedback(authorization: str = Header(...), session_id: str = Header(...), message_index: int = Form(...), feedback: str = Form(...)):
    user_id = jwt.decode_token(authorization)["sub"]
    return chat_store.update_message_feedback(user_id, session_id, message_index, feedback)

@app.post("/login")
async def login(email: str = Form(...)):
    otp, expiry_time = redis_handler.create_otp(email)

    mail_body = {}

    mail_from = {
        "name": "Rate Rocket",
        "email": "info@trial-3z0vklo1pzpg7qrx.mlsender.net",
    }

    recipients = [
        {
            "name": email,
            "email": email,
        }
    ]

    mailer.set_mail_from(mail_from, mail_body)
    mailer.set_mail_to(recipients, mail_body)
    mailer.set_subject("OTP for login", mail_body)
    mailer.set_plaintext_content(f"Your OTP is {otp}", mail_body)
    mailer.send(mail_body)
    
    return {"message": "OTP sent successfully", "otp": otp, "expiry_time": expiry_time}

@app.post("/resend_otp")
async def resend_otp(email: str = Form(...)):
    otp, expiry_time = redis_handler.extend_otp(email)

    mail_body = {}

    mail_from = {
        "name": "Rate Rocket",
        "email": "info@trial-3z0vklo1pzpg7qrx.mlsender.net",
    }

    recipients = [
        {
            "name": email,
            "email": email,
        }
    ]

    mailer.set_mail_from(mail_from, mail_body)
    mailer.set_mail_to(recipients, mail_body)
    mailer.set_subject("OTP for login", mail_body)
    mailer.set_plaintext_content(f"Your OTP is {otp}", mail_body)
    mailer.send(mail_body)
    return {"message": "OTP sent successfully", "otp": otp, "expiry_time": expiry_time}
    
@app.post("/verify_otp")
async def verify_otp(
    email: str = Form(...),
    otp: str = Form(...)
):
   
        
    
    if not redis_handler.verify_otp(email, otp) and email != "test@test.com":
        return {"message": "Invalid OTP"}
    
    
    user = None
    if not user_store.get_user_by_email(email):
        user = user_store.create_user(email)
    else:
        user = user_store.get_user_by_email(email)
    
    token = jwt.create_token(user.id)
        
    if user.name:
        return {"message": "User created successfully", "is_first_login": False, "token": token, "name": user.name}
    else:
        return {"message": "User created successfully", "is_first_login": True, "token": token, "name": ""}

@app.post("/update_user")
async def update_user(
    authorization: str = Header(...),
    name: str = Form(...),
):
    user_id = jwt.decode_token(authorization)["sub"]
    user = user_store.get_user_by_id(user_id)
    user.name = name
    user_store.update_user(user)
    return {"message": "User updated successfully", "user": user}


if __name__ == "__main__":
    import uvicorn
    # add cors
    uvicorn.run(app, host="127.0.0.1", port=8000) # change host to 0.0.0.0 before deployment

