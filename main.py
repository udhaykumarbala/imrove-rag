from fastapi import FastAPI, UploadFile, File, Header, HTTPException, Form
from typing import Optional
import uuid
from pydantic import BaseModel
from time import perf_counter
import logging

from config import settings
from llm.openai_handler import OpenAIHandler
from document_processor.processor import DocumentProcessor
from database.vector_store import VectorStore
from memory.redis_handler import RedisHandler
from fastapi.middleware.cors import CORSMiddleware
from utils.timing import timer
from database.user_store import UserStore
from database.chat_store import ChatStore
from auth.jwt import JWT

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

llm = OpenAIHandler(settings.OPENAI_API_KEY)
doc_processor = DocumentProcessor()
vector_store = VectorStore()
redis_handler = RedisHandler(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    password=settings.REDIS_PASSWORD
)

user_store = UserStore()
chat_store = ChatStore()

jwt = JWT(settings.JWT_SECRET_KEY, "HS256")

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
    session_id: Optional[str] = Header(None)
):
    if not session_id:
        session_id = str(uuid.uuid4())
    
    content = await file.read()
    text = doc_processor.process_document(content, file.filename)
    
    # Extract information using LLM
    document_info = llm.extract_document_info(text)
    
    document_id = str(uuid.uuid4())
    if document_info.get("consent", False):
        vector_store.store_document(document_info, document_id)
    
    # Check for missing information
    missing_fields = [k for k, v in document_info.items() if v == "MISSING"]

    redis_handler.save_previous_info(session_id, document_info)
    redis_handler.save_document_id(session_id, document_id)
    
    response = {
        "session_id": session_id,
        "document_id": document_id,
        "missing_fields": missing_fields,
        "extracted_info": document_info
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
        if response.get("consent", False):
            start = perf_counter()
            try:
                if not vector_store.check_if_document_exists(document_id):
                    vector_store.store_document(response, document_id)
                else:
                    vector_store.update_document(response, document_id)
                logger.info(f"⏱️ Vector store operation took {perf_counter() - start:.2f} seconds")
            except Exception as e:
                logger.error(f"Error handling vector store: {e}")
        
        # Time conversation update
        start = perf_counter()
        conversation.extend([
            {"role": "user", "content": request.message},
            {"role": "assistant", "content": response}
        ])
        redis_handler.save_conversation(session_id, conversation)
        if response.get("extracted_info", None):
            redis_handler.save_previous_info(session_id, response.get("extracted_info", {}))
        logger.info(f"⏱️ Conversation update took {perf_counter() - start:.2f} seconds")
        
        return {
            "response": response,
            "session_id": session_id
        }
    except Exception as e:
        logger.error(f"Error in upload_chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/kv-chat")
@timer
async def chat(
    request: ChatRequest,
    session_id: str = Header(...)
):
    if not session_id:
        session_id = str(uuid.uuid4())
    
    conversation = redis_handler.get_conversation(session_id)
    
    # Define system prompts
    GENERAL_LENDING_PROMPT = """You are a knowledgeable lending expert. Your role is to:
    1. Provide clear, accurate explanations of lending concepts, terms, and processes
    2. Use simple language while maintaining technical accuracy
    3. Give practical examples when helpful
    4. Break down complex topics into understandable parts
    5. Provide balanced information about pros and cons
    6. Avoid making specific recommendations unless explicitly asked
    7. Always maintain a professional yet approachable tone

    Focus on educating users about:
    - Loan types and their characteristics
    - Common lending terms and definitions
    - General lending processes and requirements
    - Industry standard practices
    - Important considerations for borrowers
    """

    GENERAL_HELP_PROMPT = """You are a helpful lending assistant. Your role is to:
    1. Provide general information about lending, loans, and the lending process
    2. Only search for specific lenders when user provides at least one specific requirement
    3. Always maintain a helpful and professional tone

    If the user hasn't provided any specific requirements but is asking about lenders, 
    politely ask them for more information to provide personalized recommendations."""

    NEED_REQUIREMENTS_PROMPT = """You are a helpful lending assistant. 
    If users want specific lender recommendations, ask them for requirements like:
       - Loan amount needed
       - Purpose of loan (business, personal, real estate, etc.)
       - Preferred loan term
       - Location
       - Credit score range (if they're comfortable sharing)
       - Any specific requirements they have
    
    Do not search for specific lenders without requirements.
    """

    SEARCH_PROMPT = """You are a helpful lending assistant. Based on the user's requirements, 
    here are relevant lenders from our knowledge base with in the single quotes: '{kb_results}'

    Please analyze these options and provide a curated response that:
    1. Matches their requirements
    2. Highlights key benefits
    3. Points out important considerations
    4. Suggests next steps

    Do not search for specific lenders without requirements or names mentioned in current or previous conversation, instead ask for requirements to search for relevant lenders.

    Keep the response clear and concise."""

    # Analyze intent
    intent = await llm.analyze_intent(request.message, conversation)
    
    # Generate appropriate response based on intent
    context = []
    
    if intent == 'general_lending':
        context.append({
            "role": "system",
            "content": GENERAL_LENDING_PROMPT
        })
    elif intent == 'search' or intent == 'more_info':
        kb_results = vector_store.search_documents(request.message) if request.context_type in ["kb", "both"] else []
        if kb_results:
            context.append({
                "role": "system",
                "content": SEARCH_PROMPT.format(kb_results=str(kb_results))
            })
    elif intent == 'others':
        # Either general help or need to ask for requirements
        return {
            "response": "I'm sorry, I don't understand that. Please ask me about lending or loan options.",
            "session_id": session_id,
            "intent": intent
        }
    elif intent == 'need_requirements':
        context.append({
            "role": "system",
            "content": SEARCH_PROMPT
        })
    else:
        context.append({
            "role": "system",
            "content": GENERAL_HELP_PROMPT
        })
    
    context.extend(conversation)
    
    # Generate response
    response = await llm.generate_response(request.message, context)
    
    # Update conversation history
    conversation.extend([
        {"role": "user", "content": request.message},
        {"role": "assistant", "content": response}
    ])
    redis_handler.save_conversation(session_id, conversation)
    
    return {
        "response": response,
        "session_id": session_id,
        "intent": intent
    }

@app.post("/login")
async def login(email: str = Form(...)):
    otp, expiry_time = redis_handler.create_otp(email)
    return {"message": "OTP sent successfully", "otp": otp, "expiry_time": expiry_time}

@app.post("/resend_otp")
async def resend_otp(email: str = Form(...)):
    otp, expiry_time = redis_handler.extend_otp(email)
    return {"message": "OTP sent successfully", "otp": otp, "expiry_time": expiry_time}
    
@app.post("/verify_otp")
async def verify_otp(
    email: str = Form(...),
    otp: str = Form(...)
):
    if not redis_handler.verify_otp(email, otp):
        return {"message": "Invalid OTP"}
    
    user = None
    if not user_store.get_user_by_email(email):
        user = user_store.create_user(email)
    else:
        user = user_store.get_user_by_email(email)
    
    token = jwt.create_token(user.id)
        
    if user.name:
        return {"message": "User created successfully", "is_first_login": False, "token": token}
    else:
        return {"message": "User created successfully", "is_first_login": True, "token": token}

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
    uvicorn.run(app, host="0.0.0.0", port=8000)

