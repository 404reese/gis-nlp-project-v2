import math

from fastapi import APIRouter, HTTPException
from app.models.schemas import GenerateRequest, GenerateResponse
from app.services.groq_client import call_groq, parse_json_safely

router = APIRouter()

MAX_NEAREST_KM = 6.0


def _partial_match(name_key: str, lookup: dict):
    """'Bandra' -> 'Bandra West'; 'Dadar West Station' -> 'Dadar West'."""
    if not name_key:
        return None
    for key, loc in lookup.items():
        if key and (key in name_key or name_key in key):
            return loc
    return None


def _nearest(lat, lon, locations):
    try:
        lat, lon = float(lat), float(lon)
    except (TypeError, ValueError):
        return None
    best, best_d = None, MAX_NEAREST_KM
    for loc in locations:
        try:
            llat, llng = float(loc["lat"]), float(loc.get("lng", loc.get("lon")))
        except (KeyError, TypeError, ValueError):
            continue
        # equirectangular approximation is plenty at city scale
        dy = (llat - lat) * 111.0
        dx = (llng - lon) * 111.0 * math.cos(math.radians(lat))
        d = math.hypot(dx, dy)
        if d < best_d:
            best, best_d = loc, d
    return best


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
            loc = location_lookup.get(name_key) or _partial_match(name_key, location_lookup)
            if loc:
                area["metrics_source"] = loc.get("name")
            else:
                # Area isn't one of our scored locations (e.g. "Marine Drive"): borrow the
                # metrics of the nearest one, and say so, rather than showing an empty card.
                loc = _nearest(area.get("lat"), area.get("lon"), LOCATIONS)
                if not loc:
                    continue
                area["metrics_source"] = f"{loc.get('name')} (nearest scored area)"
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
