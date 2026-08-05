"""POST /site-eval — a grounded "what's at this point?" real-estate site card."""
from typing import Any, Dict

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.services.site_evaluator import evaluate_site

router = APIRouter()


class SiteEvalRequest(BaseModel):
    lat: float
    lng: float
    city_id: int = 1
    radius_m: int = Field(1500, ge=250, le=5000)


@router.post("/site-eval")
async def site_eval(req: SiteEvalRequest) -> Dict[str, Any]:
    return await evaluate_site(req.lat, req.lng, req.city_id, req.radius_m)
