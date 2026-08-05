"""POST /business-estimate — location-aware startup cost breakdown for a business."""
from typing import Any, Dict, List, Optional

from fastapi import APIRouter
from pydantic import BaseModel

from app.services.business_estimator import estimate_business

router = APIRouter()


class BusinessEstimateRequest(BaseModel):
    business_type: str
    lat: float
    lng: float
    city_id: int = 1
    size_sqft: Optional[int] = None
    tier: str = "standard"  # economy | standard | premium


@router.post("/business-estimate")
async def business_estimate(req: BusinessEstimateRequest) -> Dict[str, Any]:
    return await estimate_business(
        req.business_type.strip(), req.lat, req.lng, req.city_id, req.size_sqft, req.tier
    )
