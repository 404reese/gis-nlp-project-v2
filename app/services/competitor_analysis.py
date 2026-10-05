"""Competitor + catchment analysis for a point and a business type.

Answers "who else is here, how much demand is around, and is there a better gap nearby?"
entirely from the loaded PostGIS data (poi.place, transport.stop):

  * competitors — same-category POIs inside the radius (listed, nearest first)
  * saturation  — competitor density per km² bucketed into low / moderate / high / saturated
  * catchment   — amenity + transit counts that drive demand for this business type, 0-100 index
  * gaps        — a grid scan around the point ranking spots by demand ÷ competition, so the
                  user can see where the same business would face less saturation

Thresholds and demand weights are heuristics (stated in the response `note`), the counts
and locations are measured.
"""
from __future__ import annotations

import math

from sqlalchemy import text

from app.db_spatial import get_engine
from app.services.business_estimator import GENERIC_BENCH, REV_BENCH
from app.services.site_evaluator import AMENITY_BUCKETS, BUCKET_ORDER

# Which catchment drivers matter for which business (weights sum ~1; transit counted too).
DEMAND_WEIGHTS = {
    "cafe":          {"education": 0.25, "shopping": 0.2, "banking": 0.1, "healthcare": 0.05, "food": 0.1, "transit": 0.3},
    "restaurant":    {"shopping": 0.25, "education": 0.1, "banking": 0.1, "healthcare": 0.05, "food": 0.1, "transit": 0.4},
    "pharmacy":      {"healthcare": 0.5, "shopping": 0.15, "education": 0.05, "banking": 0.05, "food": 0.0, "transit": 0.25},
    "clinic":        {"healthcare": 0.2, "shopping": 0.15, "education": 0.1, "banking": 0.05, "food": 0.0, "transit": 0.5},
    "gym":           {"education": 0.2, "shopping": 0.15, "banking": 0.1, "healthcare": 0.0, "food": 0.05, "transit": 0.5},
    "grocery store": {"shopping": 0.2, "education": 0.1, "banking": 0.05, "healthcare": 0.05, "food": 0.1, "transit": 0.5},
}
DEFAULT_WEIGHTS = {"shopping": 0.25, "education": 0.15, "banking": 0.1, "healthcare": 0.1, "food": 0.1, "transit": 0.3}
BUCKET_CAP = {"healthcare": 40, "education": 25, "food": 40, "banking": 15, "shopping": 30, "transit": 12}

GRID = 5          # GRID x GRID candidate spots
CELL_R_M = 500    # catchment radius used for each candidate spot


def _km(lat1, lng1, lat2, lng2) -> float:
    dy = (lat2 - lat1) * 111.0
    dx = (lng2 - lng1) * 111.0 * math.cos(math.radians(lat1))
    return math.hypot(dx, dy)


def _bucket_counts(points, lat, lng, r_km) -> dict:
    counts = {b: 0 for b in BUCKET_ORDER}
    for p in points:
        if _km(lat, lng, p["lat"], p["lng"]) <= r_km:
            b = AMENITY_BUCKETS.get(p["category"])
            if b:
                counts[b] += 1
    return counts


def _demand(counts: dict, transit_n: int, weights: dict) -> int:
    merged = {**counts, "transit": transit_n}
    score = sum(w * min(merged.get(k, 0) / BUCKET_CAP[k], 1.0) for k, w in weights.items())
    return round(100 * score / (sum(weights.values()) or 1))


def _saturation(density: float) -> dict:
    if density < 5:
        return {"label": "low", "text": "Few competitors — room for another."}
    if density < 15:
        return {"label": "moderate", "text": "Healthy competition; differentiate to stand out."}
    if density < 30:
        return {"label": "high", "text": "Crowded — need a clear edge to win customers."}
    return {"label": "saturated", "text": "Very crowded — expect to split demand many ways."}


async def analyze_competition(lat: float, lng: float, business_type: str,
                              city_id: int = 1, radius_m: int = 1500) -> dict:
    btype = business_type.strip().lower()
    cats = list(REV_BENCH.get(btype, GENERIC_BENCH)[0])
    if not cats:
        cats = [btype.replace(" ", "_")]  # unknown type: try its own name as a POI category
    weights = DEMAND_WEIGHTS.get(btype, DEFAULT_WEIGHTS)

    fetch_m = int(radius_m * 1.5)  # grid cells extend past the main radius
    engine = get_engine()
    async with engine.connect() as conn:
        pois = (await conn.execute(text(
            """
            SELECT name, lower(category), ST_Y(geom), ST_X(geom)
            FROM poi.place
            WHERE city_id = :c
              AND ST_DWithin(geom::geography,
                             ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography, :r)
            """
        ), {"c": city_id, "lng": lng, "lat": lat, "r": fetch_m})).fetchall()
        stops = (await conn.execute(text(
            """
            SELECT ST_Y(geom), ST_X(geom) FROM transport.stop
            WHERE city_id = :c
              AND ST_DWithin(geom::geography,
                             ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography, :r)
            """
        ), {"c": city_id, "lng": lng, "lat": lat, "r": fetch_m})).fetchall()

    points = [{"name": n, "category": c or "", "lat": float(y), "lng": float(x)} for n, c, y, x in pois]
    stop_pts = [(float(y), float(x)) for y, x in stops]
    r_km = radius_m / 1000

    # --- competitors inside the radius ---
    competitors = []
    for p in points:
        if p["category"] in cats:
            d = _km(lat, lng, p["lat"], p["lng"])
            if d <= r_km:
                competitors.append({
                    "name": p["name"] or p["category"].replace("_", " ").title(),
                    "category": p["category"], "lat": p["lat"], "lng": p["lng"],
                    "distance_m": round(d * 1000),
                })
    competitors.sort(key=lambda c: c["distance_m"])
    area_km2 = math.pi * r_km ** 2
    density = len(competitors) / area_km2

    # --- catchment demand for the centre ---
    counts = _bucket_counts(points, lat, lng, r_km)
    transit_n = sum(1 for sy, sx in stop_pts if _km(lat, lng, sy, sx) <= r_km)
    demand = _demand(counts, transit_n, weights)

    # --- gap scan: where is demand high relative to competition? ---
    cell_km = CELL_R_M / 1000
    span = r_km * 0.9
    step = (2 * span) / (GRID - 1)
    cos_lat = math.cos(math.radians(lat))
    cands = []
    for i in range(GRID):
        for j in range(GRID):
            dy_km = -span + i * step
            dx_km = -span + j * step
            clat = lat + dy_km / 111.0
            clng = lng + dx_km / (111.0 * cos_lat)
            n_comp = sum(1 for p in points if p["category"] in cats
                         and _km(clat, clng, p["lat"], p["lng"]) <= cell_km)
            c_counts = _bucket_counts(points, clat, clng, cell_km)
            c_transit = sum(1 for sy, sx in stop_pts if _km(clat, clng, sy, sx) <= cell_km)
            c_demand = _demand(c_counts, c_transit, weights)
            cands.append({
                "lat": round(clat, 5), "lng": round(clng, 5),
                "demand": c_demand, "competitors": n_comp,
                "opportunity": round(c_demand / (1 + n_comp), 1),
                "distance_m": round(math.hypot(dx_km, dy_km) * 1000),
            })
    # Only meaningful if the spot actually has some demand.
    best = sorted((c for c in cands if c["demand"] >= 15), key=lambda c: -c["opportunity"])[:3]

    centre_n500 = sum(1 for c in competitors if c["distance_m"] <= CELL_R_M)
    centre_opp = round(_demand(_bucket_counts(points, lat, lng, cell_km),
                               sum(1 for sy, sx in stop_pts if _km(lat, lng, sy, sx) <= cell_km),
                               weights) / (1 + centre_n500), 1)

    sat = _saturation(density)
    return {
        "business_type": business_type,
        "radius_m": radius_m,
        "competitor_categories": cats,
        "competitors": {
            "count": len(competitors),
            "density_per_km2": round(density, 1),
            "nearest_m": competitors[0]["distance_m"] if competitors else None,
            "items": competitors[:60],
        },
        "saturation": sat,
        "catchment": {
            "demand_index": demand,
            "amenities": counts,
            "transit_stops": transit_n,
            "demand_per_competitor": round(demand / (1 + len(competitors)), 1),
        },
        "gaps": {
            "this_spot_opportunity": centre_opp,
            "suggestions": [g for g in best if g["opportunity"] > centre_opp * 1.15],
        },
        "note": (
            f"Competitors = {', '.join(cats)} places within {radius_m / 1000:.1f} km (OSM). Saturation "
            "bands (<5 / 5-15 / 15-30 / 30+ per km²) and the demand weights are heuristics. "
            f"Gap scan scores a {GRID}x{GRID} grid by demand index ÷ (1 + competitors within "
            f"{CELL_R_M} m); suggestions need a ≥15% better score than this spot."
        ),
    }
