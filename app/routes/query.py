from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from app.database import get_or_create_chat, chat_collection
from app.services.groq_client import call_llm

router = APIRouter()

class QueryRequest(BaseModel):
    chat_id: Optional[str] = None
    message: str

class QueryResponse(BaseModel):
    chat_id: str
    text: str
    locations: Optional[List[Dict[str, Any]]] = None

@router.post("/query", response_model=QueryResponse)
def handle_query(request: QueryRequest):
    from app.main import rank_locations
    
    # 1. Get/create chat
    chat = get_or_create_chat(request.chat_id)
    chat_id = chat["chat_id"]
    
    # 2. Add user message
    user_msg = {
        "role": "user",
        "text": request.message,
        "timestamp": datetime.now(timezone.utc)
    }
    chat["messages"].append(user_msg)
    
    # 3. Send last 10 messages to call_llm
    llm_response = call_llm(chat["messages"])
    text = llm_response.get("text", "")
    filters = llm_response.get("filters")
    
    # 4. If filters exist -> run rank_locations
    locations = []
    if filters:
        locations = rank_locations(filters)
        
    # 5. Save assistant response in MongoDB
    assistant_msg = {
        "role": "assistant",
        "text": text,
        "filters": filters,
        "results": locations,
        "timestamp": datetime.now(timezone.utc)
    }
    chat["messages"].append(assistant_msg)
    
    # Update document in MongoDB
    chat_collection.update_one(
        {"chat_id": chat_id},
        {"$set": {"messages": chat["messages"], "updated_at": datetime.now(timezone.utc)}}
    )
    
    # 6. Return
    return QueryResponse(
        chat_id=chat_id,
        text=text,
        locations=locations if locations else None
    )
