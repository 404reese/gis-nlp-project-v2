"""Migrate the curated crime dataset (app/data/crime.json) into crime.area points."""
from __future__ import annotations

import json
import os

from sqlalchemy import text

CRIME_PATH = os.path.join(os.path.dirname(__file__), "..", "app", "data", "crime.json")


def _ensure_table(engine) -> None:
    """Additive migration so live DBs (already initialized) gain crime.area."""
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS crime.area (
                    id           BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                    city_id      BIGINT NOT NULL REFERENCES core.city(id) ON DELETE CASCADE,
                    name         TEXT,
                    zone         TEXT,
                    safety_score INT,
                    risk_level   TEXT,
                    breakdown    JSONB,
                    geom         geometry(Point, 4326)
                );
                """
            )
        )
        conn.execute(
            text("CREATE INDEX IF NOT EXISTS idx_crimearea_geom ON crime.area USING GIST (geom)")
        )
        conn.execute(
            text("CREATE INDEX IF NOT EXISTS idx_crimearea_city ON crime.area (city_id)")
        )
        # Keep the read-only role's grants current for the new table.
        conn.execute(text("GRANT SELECT ON crime.area TO geo_readonly"))


def ingest_crime(engine, city_id: int) -> int:
    if not os.path.exists(CRIME_PATH):
        print(f"    crime: file not found at {CRIME_PATH}")
        return 0
    with open(CRIME_PATH, "r", encoding="utf-8") as f:
        payload = json.load(f)
    locations = payload.get("locations", []) if isinstance(payload, dict) else payload

    _ensure_table(engine)
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM crime.area WHERE city_id = :id"), {"id": city_id})
        n = 0
        for loc in locations:
            cd = loc.get("crime_data", {}) or {}
            lat, lng = loc.get("lat"), loc.get("lng")
            if lat is None or lng is None:
                continue
            conn.execute(
                text(
                    """
                    INSERT INTO crime.area
                        (city_id, name, zone, safety_score, risk_level, breakdown, geom)
                    VALUES
                        (:city_id, :name, :zone, :score, :risk, :breakdown,
                         ST_SetSRID(ST_MakePoint(:lng, :lat), 4326))
                    """
                ),
                {
                    "city_id": city_id,
                    "name": loc.get("name"),
                    "zone": loc.get("zone"),
                    "score": cd.get("safety_score"),
                    "risk": cd.get("risk_level"),
                    "breakdown": json.dumps(cd),
                    "lng": lng,
                    "lat": lat,
                },
            )
            n += 1
    return n
