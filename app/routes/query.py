from fastapi import APIRouter, HTTPException
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
    filters: Optional[Dict[str, Any]] = None
    locations: Optional[List[Dict[str, Any]]] = None

class ChatMessage(BaseModel):
    role: str
    text: str
    timestamp: Optional[datetime] = None
    filters: Optional[Dict[str, Any]] = None
    results: Optional[List[Dict[str, Any]]] = None

class ChatDetailResponse(BaseModel):
    chat_id: str
    messages: List[ChatMessage]
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class ChatSummary(BaseModel):
    chat_id: str
    title: str
    last_message: str
    updated_at: Optional[datetime] = None
    message_count: int

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
        filters=filters if filters else None,
        locations=locations if locations else None
    )

@router.get("/chats", response_model=List[ChatSummary])
def list_chats():
    summaries: List[ChatSummary] = []
    chats = (
        chat_collection.find(
            {},
            {
                "chat_id": 1,
                "messages": 1,
                "updated_at": 1,
            },
        )
        .sort("updated_at", -1)
        .limit(50)
    )

    for chat in chats:
        messages = chat.get("messages", [])
        title = "New chat"
        for msg in messages:
            if msg.get("role") == "user" and msg.get("text"):
                title = msg.get("text")[:60]
                break

        last_message = ""
        if messages:
            last_message = messages[-1].get("text", "")

        summaries.append(
            ChatSummary(
                chat_id=chat.get("chat_id"),
                title=title,
                last_message=last_message,
                updated_at=chat.get("updated_at"),
                message_count=len(messages),
            )
        )

    return summaries

@router.get("/chats/{chat_id}", response_model=ChatDetailResponse)
def get_chat(chat_id: str):
    chat = chat_collection.find_one({"chat_id": chat_id})
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    return ChatDetailResponse(
        chat_id=chat.get("chat_id"),
        messages=chat.get("messages", []),
        created_at=chat.get("created_at"),
        updated_at=chat.get("updated_at"),
    )
