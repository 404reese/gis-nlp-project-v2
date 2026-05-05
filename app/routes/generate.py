from fastapi import APIRouter, HTTPException
from app.models.schemas import GenerateRequest, GenerateResponse
from app.services.groq_client import call_groq, parse_json_safely

router = APIRouter()

@router.post("/generate", response_model=GenerateResponse)
async def generate_areas(request: GenerateRequest):
    prompt = f"""You are a geospatial intelligence system for Mumbai.

Generate top 5 relevant areas for the query: "{request.query}"

Rules:
- Return ONLY valid JSON
- No markdown, no explanation outside JSON
- Score between 0 and 1
- Use real Mumbai areas

Format:
{{
  "use_case": "",
  "areas": [
    {{
      "name": "",
      "lat": 0.0,
      "lon": 0.0,
      "score": 0.0,
      "reason": ""
    }}
  ],
  "summary": ""
}}
"""
    try:
        raw_response = call_groq(prompt)
        parsed_data = parse_json_safely(raw_response)
        from app.main import LOCATIONS

        location_lookup = {
            str(loc.get("name", "")).strip().lower(): loc
            for loc in LOCATIONS
        }

        for area in parsed_data.get("areas", []):
            name_key = str(area.get("name", "")).strip().lower()
            loc = location_lookup.get(name_key)
            if not loc:
                continue
            area["area_type"] = loc.get("area_type")
            area["footfall"] = loc.get("footfall")
            area["youth"] = loc.get("youth")
            area["rent"] = loc.get("rent")
            area["access"] = loc.get("access")
            area["competition"] = loc.get("competition")
            area["flood"] = loc.get("flood")
            area["traffic"] = loc.get("traffic")

        return GenerateResponse(**parsed_data)
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")
