import os
import uuid
from datetime import datetime, timezone
from pymongo import MongoClient

# Import config first so .env variables are loaded into os.environ
import app.config  # noqa: F401

# Get MONGODB_URI from environment variables, fallback to localhost for local dev
MONGO_URI = os.environ.get("MONGODB_URI", "mongodb://localhost:27017")

client = MongoClient(MONGO_URI)
db = client["sentinel"]
chat_collection = db["alpha-station-dev"]

print(f"[MongoDB] Connected to: {MONGO_URI}")
print(f"[MongoDB] Database: sentinel | Collection: alpha-station-dev")

def get_or_create_chat(chat_id: str | None):
    """
    Retrieve an existing chat by chat_id or create a new one.
    """
    if chat_id:
        chat = chat_collection.find_one({"chat_id": chat_id})
        if chat:
            # Convert ObjectId to string if needed by FastAPI, or just return as is
            # We can return the chat dictionary directly.
            chat["_id"] = str(chat["_id"])
            return chat

    # Create new chat
    new_chat_id = chat_id if chat_id else str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    
    new_chat = {
        "chat_id": new_chat_id,
        "messages": [],
        "created_at": now,
        "updated_at": now
    }
    
    # Insert the new chat into MongoDB
    result = chat_collection.insert_one(new_chat)
    
    # Optional: ensure '_id' is easily serializable
    new_chat["_id"] = str(result.inserted_id)
    
    return new_chat
