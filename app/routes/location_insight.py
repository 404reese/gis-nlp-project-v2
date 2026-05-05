from fastapi import APIRouter, HTTPException
from app.models.schemas import LocationInsightRequest, LocationInsightResponse
from app.services.groq_client import call_groq, parse_json_safely
import json

router = APIRouter()

@router.post("/location-insight", response_model=LocationInsightResponse)
async def location_insight(request: LocationInsightRequest):
    location_json = json.dumps(request.location, indent=2)
    
    # Format conversation history for context
    convo_text = ""
    if request.conversation:
        convo_lines = []
        for msg in request.conversation[-10:]:
            sender = msg.get("sender", msg.get("role", "user"))
            text = msg.get("text", msg.get("content", ""))
            convo_lines.append(f"{sender}: {text}")
        convo_text = "\n".join(convo_lines)
    
    prompt = f"""You are a geospatial intelligence analyst for Mumbai.

User's original query: "{request.query}"

User's conversation history:
{convo_text if convo_text else "No prior conversation."}

Selected Location Data:
{location_json}

Task:
Write a detailed analysis (4-6 sentences) explaining WHY this specific location is the best fit for what the user is looking for. Reference the user's requirements from the conversation and tie them to the location's metrics (footfall, youth, rent, access, competition, flood risk, traffic, area type).

Then, at the end, mention 1-2 honest cons or trade-offs of this location that the user should be aware of.

Use a professional but accessible tone. Be specific — reference actual metric values.

Return STRICT JSON:
{{
  "insight": "Your detailed analysis here. Include pros tied to user needs, then end with 1-2 cons."
}}
"""
    try:
        raw_response = call_groq(prompt)
        parsed_data = parse_json_safely(raw_response)
        return LocationInsightResponse(**parsed_data)
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")
