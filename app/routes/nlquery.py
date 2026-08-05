"""POST /nlquery — natural language -> PostGIS -> GeoJSON answer layer."""
from typing import Any, Dict, List, Optional

from fastapi import APIRouter
from pydantic import BaseModel

from app.services.geo_engine import run_nl_query

router = APIRouter()


class NLQueryRequest(BaseModel):
    question: str
    city_id: int = 1


class NLQueryResponse(BaseModel):
    ok: bool
    city_id: int
    question: str
    is_clear: bool
    task_type: Optional[str] = None
    message: str
    answer: Optional[Dict[str, Any]] = None  # GeoJSON FeatureCollection
    count: int
    sql: Optional[str] = None
    explanation: Optional[str] = None
    attempts: List[Dict[str, Any]] = []


@router.post("/nlquery", response_model=NLQueryResponse)
async def nlquery(req: NLQueryRequest):
    result = await run_nl_query(req.question.strip(), req.city_id)
    return NLQueryResponse(**result)
