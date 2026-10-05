"""POST /competitor-analysis — who competes here, how much demand surrounds it, where are gaps."""
from typing import Any, Dict

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.services.competitor_analysis import analyze_competition

router = APIRouter()


class CompetitionRequest(BaseModel):
    lat: float
    lng: float
    business_type: str
    city_id: int = 1
    radius_m: int = Field(1500, ge=250, le=3000)


@router.post("/competitor-analysis")
async def competitor_analysis(req: CompetitionRequest) -> Dict[str, Any]:
    return await analyze_competition(req.lat, req.lng, req.business_type, req.city_id, req.radius_m)
