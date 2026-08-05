import json
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import analyze, generate, explain, query, location_insight, properties, health, nlquery, business, site
from app.db_spatial import dispose_engines

LOCATIONS = []

@asynccontextmanager
async def lifespan(app: FastAPI):
    global LOCATIONS
    file_path = os.path.join(os.path.dirname(__file__), "data", "crime.json")
    try:
        with open(file_path, "r") as f:
            payload = json.load(f)
            if isinstance(payload, dict):
                LOCATIONS = payload.get("locations", [])
            elif isinstance(payload, list):
                LOCATIONS = payload
            else:
                LOCATIONS = []
    except FileNotFoundError:
        print(f"Dataset not found at {file_path}")
    yield
    LOCATIONS.clear()
    await dispose_engines()

app = FastAPI(
    title="Geospatial Query System API",
    description="Minimal FastAPI backend for an AI-powered Geospatial Query System with NLP + GIS integration focused on Mumbai.",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(nlquery.router, tags=["NL Query"])
app.include_router(business.router, tags=["Business"])
app.include_router(site.router, tags=["Site Evaluation"])
app.include_router(analyze.router, tags=["Analyze"])
app.include_router(generate.router, tags=["Generate"])
app.include_router(explain.router, tags=["Explain"])
app.include_router(query.router, tags=["Query"])
app.include_router(location_insight.router, tags=["Location Insight"])
app.include_router(properties.router, tags=["Properties"])

def rank_locations(filters: dict) -> list:
    """
    Score locations using predefined weights.
    Returns top 5 locations.
    """
    scored = []
    if not isinstance(LOCATIONS, list):
        return scored

    for loc in LOCATIONS:
        if not isinstance(loc, dict):
            continue

        score = (
            0.3 * loc.get("footfall", 0) +
            0.25 * loc.get("youth", 0) +
            0.2 * loc.get("access", 0) +
            0.15 * (10 - loc.get("rent", 0)) +
            0.1 * (10 - loc.get("competition", 0))
        )
        scored.append({
            "name": loc.get("name"),
            "lat": loc.get("lat"),
            "lng": loc.get("lng"),
            "score": round(score, 2),
            "reason": f"Strong overall metrics with a score of {score:.2f}."
        })
    
    # Sort descending by score and get top 5
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:5]

@app.get("/")
async def root():
    return {"message": "Welcome to the Geospatial Query System API for Mumbai."}


@app.get("/locations")
async def get_locations():
    return LOCATIONS
