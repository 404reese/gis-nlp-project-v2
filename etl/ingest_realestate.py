"""Ingest the Mumbai house-price CSV as a real spatial layer.

The CSV has no coordinates, so we geocode each unique *region* once (Nominatim, cached
to disk) and place its listings at the region centroid with a small deterministic offset
so the points form a readable cloud rather than stacking. Region-level geolocation is
honest for price analysis; per-address geocoding (76k calls) is out of scope for M1.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import time

import geopandas as gpd
import pandas as pd
import requests
from shapely.geometry import Point

from etl.db import delete_city_rows, exec_sql, stage_gdf

CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "app", "data", "Mumbai House Prices.csv")
CACHE_PATH = os.path.join(os.path.dirname(__file__), "cache", "geocode.json")
NOMINATIM = "https://nominatim.openstreetmap.org/search"


def _load_cache() -> dict:
    if os.path.exists(CACHE_PATH):
        with open(CACHE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_cache(cache: dict) -> None:
    os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f)


def _geocode(region: str, city: str, country: str, cache: dict):
    key = f"{region}|{city}|{country}"
    if key in cache:
        return cache[key]
    try:
        r = requests.get(
            NOMINATIM,
            params={"q": f"{region}, {city}, {country}", "format": "json", "limit": 1},
            headers={"User-Agent": "GeoQuerySentinel/0.1 (academic project)"},
            timeout=30,
        )
        js = r.json()
        cache[key] = [float(js[0]["lat"]), float(js[0]["lon"])] if js else None
    except Exception as exc:  # noqa: BLE001
        print(f"    geocode failed for {region}: {exc}")
        cache[key] = None
    time.sleep(1.1)  # Nominatim usage policy: <= 1 req/s
    return cache[key]


def _jitter(region: str, idx: int):
    """Deterministic ~±700 m offset from a hash, so identical-region points spread."""
    h = int(hashlib.md5(f"{region}{idx}".encode()).hexdigest(), 16)
    ang = (h % 360) * math.pi / 180.0
    rad = ((h >> 9) % 1000) / 1000.0 * 0.006  # up to ~0.006 deg
    return math.cos(ang) * rad, math.sin(ang) * rad


def ingest_realestate(engine, city_id: int, city="Mumbai", country="India") -> int:
    if not os.path.exists(CSV_PATH):
        print(f"    real-estate: CSV not found at {CSV_PATH}")
        return 0
    df = pd.read_csv(CSV_PATH)
    df = df[df["region"].notna()].copy()

    cache = _load_cache()
    regions = sorted(df["region"].dropna().unique())
    print(f"    geocoding {len(regions)} unique regions (cached)...")
    coords = {reg: _geocode(reg, city, country, cache) for reg in regions}
    _save_cache(cache)

    rows = []
    for idx, row in df.reset_index(drop=True).iterrows():
        base = coords.get(row["region"])
        if not base:
            continue
        dlat, dlon = _jitter(str(row["region"]), idx)
        rows.append(
            {
                "city_id": city_id,
                "locality": row.get("locality"),
                "bhk": int(row["bhk"]) if pd.notna(row.get("bhk")) else None,
                "type": row.get("type"),
                "area_sqft": float(row["area"]) if pd.notna(row.get("area")) else None,
                "price": float(row["price"]) if pd.notna(row.get("price")) else None,
                "price_unit": row.get("price_unit"),
                "status": row.get("status"),
                "age": row.get("age"),
                "geometry": Point(base[1] + dlon, base[0] + dlat),
            }
        )
    if not rows:
        print("    real-estate: nothing geocoded")
        return 0

    g = gpd.GeoDataFrame(rows, geometry="geometry", crs="EPSG:4326")
    stage_gdf(g, engine, "realestate_listing")
    delete_city_rows(engine, "realestate.listing", city_id)
    exec_sql(
        engine,
        """
        INSERT INTO realestate.listing
            (city_id, locality, bhk, type, area_sqft, price, price_unit, status, age, geom)
        SELECT city_id, locality, bhk, type, area_sqft, price, price_unit, status, age,
               geom::geometry(Point, 4326)
        FROM staging.realestate_listing
        """,
    )
    return len(g)
