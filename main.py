from fastapi import FastAPI, UploadFile, File, Header, HTTPException
from typing import Optional
import uuid
from pydantic import BaseModel

from config import settings
from llm.openai_handler import OpenAIHandler
from document_processor.processor import DocumentProcessor
from database.vector_store import VectorStore
from memory.redis_handler import RedisHandler
from fastapi.middleware.cors import CORSMiddleware
app = FastAPI()

origins = [
    "http://localhost:3000",
    "https://rate-rocket-ai.pages.dev"
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
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

# Define request model
class ChatRequest(BaseModel):
    message: str
    document_id: Optional[str] = None
    context_type: str = "both"  # default value

@app.post("/upload")
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
    
    return response

@app.post("/upload_chat")
async def upload_chat(request: ChatRequest, session_id: str = Header(...)):
    conversation = redis_handler.get_conversation(session_id)
    previous_info = redis_handler.get_previous_info(session_id)
    document_id = redis_handler.get_document_id(session_id)
    print(f"document_id: {document_id}")
    
    if not document_id:
        return {
            "response": {
                "message": "No documents found. Please upload a document first."
            },
            "session_id": session_id
        }
    
    response = llm.extract_document_info_from_conversation(
        prompt=request.message,
        conversation=conversation,
        previous_info=previous_info
    )
    
    if response.get("consent", False):
        if not vector_store.check_if_document_exists(document_id):
            print("Storing new document")
            vector_store.store_document(response, document_id)
        else:
            print("Updating existing document")
            vector_store.update_document(response, document_id)

    # if response.get("consent", False):
    #     response["message"] = "### Data Updated in to knowledge base \n" + response.get("message", "")
    
    response["consent"] = False
    conversation.extend([
        {"role": "user", "content": request.message},
        {"role": "assistant", "content": response}
    ])
    redis_handler.save_conversation(session_id, conversation)
    redis_handler.save_previous_info(session_id, response)

    return {
        "response": response,
        "session_id": session_id
    }

@app.post("/kv-chat")
async def chat(
    request: ChatRequest,
    session_id: str = Header(...)
):
    # Get conversation history
    conversation = redis_handler.get_conversation(session_id)
    
    # Search vector store for relevant information
    kb_results = vector_store.search_documents(request.message) if request.context_type in ["kb", "both"] else []
    
    # Generate response
    context = []
    if kb_results:
        context.append({
            "role": "system",
            "content": f"you are a helpful lending assistant. You will be helping Lenders to add their loan sheets to knowledge base and curstomers to help find the best loan options. Relevant information from knowledge base: {str(kb_results)}"
        })
    context.extend(conversation)
    
    response = llm.generate_response(request.message, context)
    
    # Update conversation history
    conversation.extend([
        {"role": "user", "content": request.message},
        {"role": "assistant", "content": response}
    ])
    redis_handler.save_conversation(session_id, conversation)
    
    return {
        "response": response,
        "session_id": session_id
    }

if __name__ == "__main__":
    import uvicorn
    # add cors
    uvicorn.run(app, host="0.0.0.0", port=8000)

