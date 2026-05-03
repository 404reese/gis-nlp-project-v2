from fastapi import APIRouter, HTTPException
from app.models.schemas import ExplainRequest, ExplainResponse
from app.services.groq_client import call_groq, parse_json_safely
import json

router = APIRouter()

@router.post("/explain", response_model=ExplainResponse)
async def explain_areas(request: ExplainRequest):
    areas_json = json.dumps([area.dict() for area in request.areas], indent=2)
    prompt = f"""You are a geospatial intelligence system for Mumbai.

User Query: "{request.query}"

Selected Areas:
{areas_json}

Explain why these areas are selected.
Use professional urban planning tone.
Keep it short (3-4 lines).

Return STRICT JSON:
{{
  "explanation": ""
}}
"""
    try:
        raw_response = call_groq(prompt)
        parsed_data = parse_json_safely(raw_response)
        return ExplainResponse(**parsed_data)
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")
