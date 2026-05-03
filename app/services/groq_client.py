import requests
import json
import re
from app.config import settings

def call_groq(prompt: str) -> str:
    """
    Calls the Groq API and returns the text response.
    """
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }
    
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()  # Raise an exception for bad status codes
    data = response.json()
    
    return data["choices"][0]["message"]["content"]

def parse_json_safely(text: str) -> dict:
    """
    Safely extract JSON from Groq's response using try/except and regex fallback.
    """
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Fallback: regex to extract JSON block
        # Match anything between { and } including newlines
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
                
        # Try matching markdown code blocks if the first regex failed
        match_md = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
        if match_md:
            try:
                return json.loads(match_md.group(1))
            except json.JSONDecodeError:
                pass
                
        raise ValueError(f"Could not extract valid JSON from response. Raw text: {text}")

def call_llm(messages: list) -> dict:
    """
    Input is full conversation (last 10 messages).
    Returns a dict with 'text' and 'filters'.
    If query is vague, returns a follow-up question in 'text' instead of filters.
    Mocks response if API key is missing.
    """
    if not settings.GROQ_API_KEY or settings.GROQ_API_KEY == "mock_key":
        return {
            "text": "[MOCK] I see you are looking for a location. What kind of budget do you have in mind?",
            "filters": {
                "footfall": "high",
                "youth": "medium",
                "rent": "low",
                "purpose": "retail"
            }
        }

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    # Take the last 10 messages to maintain context and format them for the API
    recent_messages = []
    for msg in messages[-10:]:
        # Ensure we only send role and content to the API
        role = msg.get("role", "user")
        # Handle cases where the key might be 'text' or 'content'
        content = msg.get("content") or msg.get("text", "")
        recent_messages.append({"role": role, "content": content})

    system_prompt = {
        "role": "system",
        "content": (
            "You are a geospatial intelligence assistant for Mumbai. "
            "Analyze the conversation and extract location filters if the user's requirements are clear. "
            "Respond ONLY with a valid JSON object. No markdown, no extra text.\n"
            "Format:\n"
            "{\n"
            "  \"text\": \"assistant reply or follow-up question\",\n"
            "  \"filters\": {\n"
            "    \"footfall\": \"high/medium/low\",\n"
            "    \"youth\": \"high/medium/low\",\n"
            "    \"rent\": \"high/medium/low\",\n"
            "    \"purpose\": \"...\"\n"
            "  }\n"
            "}\n"
            "If the query is too vague to determine filters, omit the filters entirely or set them to null, and use 'text' to ask a follow-up question."
        )
    }

    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [system_prompt] + recent_messages,
        "response_format": {"type": "json_object"}
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        return parse_json_safely(content)
    except Exception as e:
        return {
            "text": f"Error communicating with LLM: {str(e)}",
            "filters": {}
        }
