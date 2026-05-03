from fastapi import APIRouter, HTTPException
from app.models.schemas import AnalyzeRequest, AnalyzeResponse
from app.services.groq_client import call_groq, parse_json_safely

router = APIRouter()

@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_query(request: AnalyzeRequest):
    prompt = f"""You are a geospatial AI assistant for Mumbai.

Tasks:
1. Understand the user query: "{request.query}"
2. Identify use-case (cafe, fire station, flood risk, etc.)
3. Check if query is vague

Rules:
- If vague → ask follow-up question
- If clear → confirm understanding
- Keep response conversational

Return STRICT JSON:
{{
  "is_clear": true/false,
  "use_case": "",
  "message": "",
  "required_fields": []
}}
"""
    try:
        raw_response = call_groq(prompt)
        parsed_data = parse_json_safely(raw_response)
        return AnalyzeResponse(**parsed_data)
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")
