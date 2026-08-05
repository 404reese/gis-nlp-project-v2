"""Location site-evaluation — a Felt-style "what's here?" report for any point.

Given a clicked lat/lng, this grounds a real-estate site card entirely in the PostGIS
data we already loaded (see docs/ARCHITECTURE.md):

  * comps      — nearby listings -> median price-per-sqft, price band, per-BHK breakdown
  * vs_city    — how the local ₹/sqft compares to the whole-city median (a percentile-ish read)
  * transit    — nearest stop of each mode (metro / rail / bus) and its distance
  * amenities  — counts of POIs within the radius, bucketed into human categories
  * safety     — nearest crime.area gazetteer point: safety_score + risk_level
  * locality   — best human name for the spot (nearest gazetteer area, else ward)

Everything here is measured, not modelled. The business-setup COST for a point is handled
separately by `business_estimator.py`; this module is the "should I be here?" read.
"""
from __future__ import annotations

import asyncio

from sqlalchemy import text

from app.db_spatial import get_engine

CR = 1e7  # 1 crore rupees
L = 1e5   # 1 lakh rupees

# poi.place.category -> the human bucket we show in the card. Anything unmapped is ignored
# for the headline counts (kept honest: we only bucket categories we understand).
AMENITY_BUCKETS: dict[str, str] = {
    "hospital": "healthcare", "clinic": "healthcare", "doctors": "healthcare",
    "pharmacy": "healthcare", "dentist": "healthcare",
    "school": "education", "college": "education", "university": "education",
    "kindergarten": "education", "library": "education",
    "restaurant": "food", "cafe": "food", "fast_food": "food", "bar": "food",
    "food_court": "food", "pub": "food",
    "bank": "banking", "atm": "banking",
    "supermarket": "shopping", "marketplace": "shopping", "mall": "shopping",
    "convenience": "shopping", "shop": "shopping",
}
BUCKET_ORDER = ["healthcare", "education", "food", "banking", "shopping"]


def _psf(price: float | None, unit: str | None, area: float | None) -> float | None:
    """Convert a listing's (price, unit, area) into rupees per sqft, or None if unusable."""
    if not price or not area or area <= 0:
        return None
    mult = CR if (unit or "").strip().lower().startswith("cr") else L
    return price * mult / area


def _median(values: list[float]) -> float | None:
    if not values:
        return None
    s = sorted(values)
    n = len(s)
    mid = n // 2
    return s[mid] if n % 2 else (s[mid - 1] + s[mid]) / 2


async def _comps(conn, lat: float, lng: float, city_id: int, radius_m: int) -> dict:
    rows = (await conn.execute(text(
        """
        SELECT bhk, area_sqft, price, price_unit
        FROM realestate.listing
        WHERE city_id = :c AND area_sqft > 100 AND price > 0
          AND ST_DWithin(geom::geography,
                         ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography, :r)
        """
    ), {"c": city_id, "lng": lng, "lat": lat, "r": radius_m})).fetchall()

    all_psf: list[float] = []
    by_bhk: dict[int, list[float]] = {}
    for bhk, area, price, unit in rows:
        v = _psf(price, unit, area)
        if v is None:
            continue
        all_psf.append(v)
        if bhk:
            by_bhk.setdefault(int(bhk), []).append(v)

    med = _median(all_psf)
    all_psf.sort()
    band = None
    if all_psf:
        lo = all_psf[int(len(all_psf) * 0.10)]
        hi = all_psf[min(len(all_psf) - 1, int(len(all_psf) * 0.90))]
        band = {"low": round(lo), "high": round(hi)}

    bhk_breakdown = [
        {"bhk": k, "median_psf": round(_median(v)), "count": len(v)}
        for k, v in sorted(by_bhk.items())
        if len(v) >= 2  # don't publish a "median" off a single listing
    ]

    return {
        "count": len(all_psf),
        "median_psf": round(med) if med else None,
        "band_psf": band,
        "by_bhk": bhk_breakdown,
    }


async def _city_median_psf(conn, city_id: int) -> float | None:
    row = (await conn.execute(text(
        """
        SELECT percentile_cont(0.5) WITHIN GROUP (
            ORDER BY price * (CASE WHEN lower(price_unit) LIKE 'cr%' THEN 1e7 ELSE 1e5 END)
                     / area_sqft
        )
        FROM realestate.listing
        WHERE city_id = :c AND area_sqft > 100 AND price > 0
        """
    ), {"c": city_id})).scalar()
    return float(row) if row else None


async def _transit(conn, lat: float, lng: float, city_id: int, radius_m: int) -> list[dict]:
    rows = (await conn.execute(text(
        """
        SELECT DISTINCT ON (mode) mode, name,
               ST_Distance(geom::geography,
                           ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography) AS dist_m
        FROM transport.stop
        WHERE city_id = :c
          AND ST_DWithin(geom::geography,
                         ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography, :r)
        ORDER BY mode, dist_m
        """
    ), {"c": city_id, "lng": lng, "lat": lat, "r": radius_m})).fetchall()
    return [
        {"mode": m, "name": n or m.title(), "distance_m": round(d)}
        for m, n, d in sorted(rows, key=lambda x: x[2])
    ]


async def _amenities(conn, lat: float, lng: float, city_id: int, radius_m: int) -> dict:
    rows = (await conn.execute(text(
        """
        SELECT category, COUNT(*)
        FROM poi.place
        WHERE city_id = :c
          AND ST_DWithin(geom::geography,
                         ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography, :r)
        GROUP BY category
        """
    ), {"c": city_id, "lng": lng, "lat": lat, "r": radius_m})).fetchall()
    buckets = {b: 0 for b in BUCKET_ORDER}
    for category, n in rows:
        bucket = AMENITY_BUCKETS.get((category or "").strip().lower())
        if bucket:
            buckets[bucket] += int(n)
    return buckets


async def _safety_and_locality(conn, lat: float, lng: float, city_id: int) -> dict:
    """Nearest gazetteer area gives us both a safety read and a human place name."""
    row = (await conn.execute(text(
        """
        SELECT name, safety_score, risk_level,
               ST_Distance(geom::geography,
                           ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography) AS dist_m
        FROM crime.area
        WHERE city_id = :c
        ORDER BY geom <-> ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)
        LIMIT 1
        """
    ), {"c": city_id, "lng": lng, "lat": lat})).fetchone()
    if not row:
        return {"area": None, "safety_score": None, "risk_level": None}
    name, score, risk, dist = row
    return {
        "area": name,
        "safety_score": int(score) if score is not None else None,
        "risk_level": risk,
        "distance_m": round(dist),
    }


async def _ward(conn, lat: float, lng: float, city_id: int) -> str | None:
    row = (await conn.execute(text(
        """
        SELECT name FROM admin.boundary
        WHERE city_id = :c AND kind = 'ward'
          AND ST_Contains(geom, ST_SetSRID(ST_MakePoint(:lng, :lat), 4326))
        LIMIT 1
        """
    ), {"c": city_id, "lng": lng, "lat": lat})).fetchone()
    return row[0] if row else None


def _vs_city(local: float | None, city: float | None) -> dict | None:
    if not local or not city:
        return None
    pct = (local - city) / city * 100
    if pct > 8:
        label = "above"
    elif pct < -8:
        label = "below"
    else:
        label = "around"
    return {"city_median_psf": round(city), "delta_pct": round(pct), "label": label}


async def evaluate_site(lat: float, lng: float, city_id: int = 1, radius_m: int = 1500) -> dict:
    engine = get_engine()
    async with engine.connect() as conn:
        # These are independent reads; run them concurrently on the one connection is not
        # safe (a single connection is serial), so gather across short sequential awaits is
        # fine here — the queries are all indexed and small. Keep it simple and sequential.
        comps = await _comps(conn, lat, lng, city_id, radius_m)
        city_med = await _city_median_psf(conn, city_id)
        transit = await _transit(conn, lat, lng, city_id, max(radius_m, 4000))
        amenities = await _amenities(conn, lat, lng, city_id, radius_m)
        safety = await _safety_and_locality(conn, lat, lng, city_id)
        ward = await _ward(conn, lat, lng, city_id)

    locality = safety.get("area") or ward or "this location"
    return {
        "location": {"lat": lat, "lng": lng},
        "radius_m": radius_m,
        "locality": locality,
        "ward": ward,
        "comps": comps,
        "vs_city": _vs_city(comps.get("median_psf"), city_med),
        "transit": transit,
        "amenities": amenities,
        "safety": safety,
        "note": "Prices are median sale ₹/sqft from listings within "
                f"{radius_m/1000:.1f} km. Amenity and transit counts are live OSM data.",
    }
