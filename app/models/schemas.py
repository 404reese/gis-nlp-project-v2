from pydantic import BaseModel
from typing import List, Optional

class AnalyzeRequest(BaseModel):
    query: str

class AnalyzeResponse(BaseModel):
    is_clear: bool
    use_case: str
    message: str
    required_fields: List[str]

class GenerateRequest(BaseModel):
    query: str

class Area(BaseModel):
    name: str
    lat: float
    lon: float
    score: float
    reason: str
    area_type: Optional[str] = None
    footfall: Optional[int] = None
    youth: Optional[int] = None
    rent: Optional[int] = None
    access: Optional[int] = None
    competition: Optional[int] = None
    flood: Optional[int] = None
    traffic: Optional[int] = None

class GenerateResponse(BaseModel):
    use_case: str
    areas: List[Area]
    summary: str

class ExplainRequest(BaseModel):
    areas: List[Area]
    query: str

class ExplainResponse(BaseModel):
    explanation: str

class LocationInsightRequest(BaseModel):
    location: dict
    query: str
    conversation: Optional[List[dict]] = []

class LocationInsightResponse(BaseModel):
    insight: str

