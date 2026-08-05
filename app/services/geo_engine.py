"""NL -> PostGIS query engine (multi-agent, see docs/ARCHITECTURE.md §5).

Pipeline:
  1. interpret  — is the question a clear spatial query? task type + confirmation/follow-up.
  2. generate   — schema-grounded PostGIS SQL (single SELECT, city-scoped, emits `geom`).
  3. execute    — run as the read-only role; wrap the result into a GeoJSON FeatureCollection.
  4. repair     — on a DB error, feed the error back for a corrected query (bounded retries).
  5. explain    — natural-language answer grounded in the rows actually returned.

Safety (§5.5): SQL runs as geo_readonly (SELECT-only role) with a statement timeout; we
also validate it is a single read-only statement and cap the row count.
"""
from __future__ import annotations

import asyncio
import json
import re

from sqlalchemy import text

from app.db_spatial import get_engine, get_engine_readonly
from app.services.groq_client import call_groq, parse_json_safely

MAX_FEATURES = 5000
MAX_REPAIRS = 2

# Compact, authoritative description of the queryable schema for the SQL agent.
SCHEMA_DOC = """\
All tables are in PostGIS, geometry column is `geom`, SRID 4326. Every feature table has
`city_id` — ALWAYS filter `city_id = :CITY_ID` on every table you read.

admin.boundary(name text, admin_level int, kind text /*city|ward*/, geom MultiPolygon)
roads.segment(name text, highway_class text /*motorway|trunk|primary|secondary|tertiary*/,
              maxspeed int, oneway bool, geom LineString)
transport.stop(name text, mode text /*bus|metro|rail|tram*/, geom Point)
poi.place(name text, category text, tags jsonb, geom Point)
   -- THE ONLY table of businesses/amenities. category examples: restaurant, cafe, fast_food,
   --   bar, bank, atm, hospital, clinic, doctors, pharmacy, school, college, university,
   --   police, fire_station, fuel, marketplace, cinema, place_of_worship, hotel, museum, shop
realestate.listing(locality text, bhk int, type text, area_sqft float, price float,
              price_unit text /*'Cr'=crore, 'L'=lakh*/, status text, age text, geom Point)
demo.cell(population float, density float, age_median float, income_index float, geom Polygon)
crime.area(name text, zone text, safety_score int /*0-100, higher=safer*/,
              risk_level text /*low|medium|high*/, breakdown jsonb, geom Point)
   -- ALSO a NEIGHBOURHOOD GAZETTEER: ~40 point rows named like 'Bandra West', 'Andheri East',
   --   'Powai', 'Lower Parel'. Use it to resolve colloquial area names to a location.
env.measurement(kind text /*aqi|flood_risk*/, value float, geom Geometry)

CRITICAL GROUNDING:
- Businesses/amenities (hospital, cafe, bank, school, pharmacy...) live ONLY in poi.place via
  `category`. transport.stop.mode is ONLY 'bus'|'metro'|'rail'|'tram' — NEVER an amenity.
- admin.boundary ward names are coded ('K/W Ward', 'H/E Ward') and do NOT contain neighbourhood
  names. To find things "in <area>" (e.g. "in Bandra"), resolve the area via crime.area:
    JOIN crime.area a ON a.name ILIKE '%Bandra%'
    AND ST_DWithin(p.geom::geography, a.geom::geography, 2000)   -- ~2 km around the area
- "hospital" -> category IN ('hospital','clinic','doctors'); "college/university" likewise.

RULES:
- Output ONE read-only SELECT statement. No INSERT/UPDATE/DELETE/DDL, no semicolons chaining.
- Select a geometry column ALIASED EXACTLY `geom` (SRID 4326) plus useful descriptive columns
  (name, category, price, safety_score, ...). The `geom` column is required for mapping.
- Metric distance: use geography casts, e.g.
    ST_DWithin(a.geom::geography, b.geom::geography, 1000)   -- within 1000 metres
- Match names/categories with ILIKE '%...%'. When ranking, use ORDER BY + LIMIT (<= 500).
- Never reference a table or column not listed above.
"""

_FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|alter|create|truncate|grant|revoke|copy|vacuum|call|merge|do)\b",
    re.IGNORECASE,
)


def _strip_sql(raw: str) -> str:
    """Pull SQL out of any markdown fencing the model may add."""
    m = re.search(r"```(?:sql)?\s*(.+?)\s*```", raw, re.DOTALL | re.IGNORECASE)
    sql = m.group(1) if m else raw
    return sql.strip()


def validate_select(sql: str) -> str:
    """Reject anything that isn't a single read-only SELECT/WITH statement."""
    s = _strip_sql(sql).rstrip(";").strip()
    if ";" in s:
        raise ValueError("multiple statements are not allowed")
    low = s.lower()
    if not (low.startswith("select") or low.startswith("with")):
        raise ValueError("query must be a SELECT")
    if _FORBIDDEN.search(s):
        raise ValueError("query contains a forbidden keyword")
    return s


# ---------------------------------------------------------------------------
# LLM stages (call_groq is sync; run in a thread so the event loop is free)
# ---------------------------------------------------------------------------
async def _agent_interpret(question: str, city: str) -> dict:
    prompt = f"""You are the intent parser for a geospatial query engine over a PostGIS
database covering {city}. Available data: businesses/amenities (hospitals, cafes, banks,
schools...), roads, transit stops (bus/metro/rail), real-estate listings (price, bhk),
per-area safety scores, and demographics.

Question: "{question}"

Lean towards is_clear=TRUE. A question is clear if you can tell what kind of features to map —
including by category (cafes), proximity (near a metro), named area (in Bandra), price, or
metric (safest, cheapest, densest). Mark is_clear=FALSE ONLY when the target is genuinely
unknowable (e.g. "best place?", "show me something"), and then ask a short follow-up.

Return STRICT JSON:
{{
  "is_clear": true/false,
  "task_type": "filter|proximity|ranking|aggregation|site_selection|other",
  "message": "one concise sentence: confirm what you'll map, OR ask a follow-up if vague",
  "entities": {{"any": "extracted places, categories, thresholds"}}
}}"""
    raw = await asyncio.to_thread(call_groq, prompt)
    return parse_json_safely(raw)


async def _agent_generate(question: str, city_id: int, prior_error: str | None = None,
                          empty_hint: bool = False) -> str:
    doc = SCHEMA_DOC.replace(":CITY_ID", str(city_id))
    repair = ""
    if prior_error:
        repair = (
            f"\nYour previous query failed with this database error:\n{prior_error}\n"
            "Fix it. Re-check table/column names and casts.\n"
        )
    elif empty_hint:
        repair = (
            "\nYour previous query was valid but returned 0 rows. It is likely too strict or "
            "matched the wrong table/name. Loosen it: use ILIKE '%...%' instead of '=', resolve "
            "neighbourhood names via crime.area, and/or widen the distance buffer.\n"
        )
    prompt = f"""You translate natural-language questions into PostGIS SQL.

{doc}

City id to use: {city_id}
Question: "{question}"
{repair}
Return ONLY the SQL. No explanation, no markdown."""
    raw = await asyncio.to_thread(call_groq, prompt)
    return validate_select(raw)


async def _agent_explain(question: str, sql: str, features: list, count: int, city: str) -> str:
    sample = [f.get("properties", {}) for f in features[:15]]
    prompt = f"""You explain the result of a geospatial query over {city} to a user.

Question: "{question}"
Rows returned: {count}
Sample of the returned features (properties only):
{json.dumps(sample, ensure_ascii=False)[:2500]}

Write 2-4 sentences: what was found and the key takeaway. Be specific and reference actual
values where useful. If 0 rows, say nothing matched and suggest a looser criterion. Plain text."""
    return (await asyncio.to_thread(call_groq, prompt)).strip()


# ---------------------------------------------------------------------------
async def _execute_to_geojson(inner_sql: str, city_id: int) -> tuple[dict, int]:
    """Run the (validated) inner SELECT and fold it into a GeoJSON FeatureCollection."""
    wrapped = text(
        f"""
        SELECT jsonb_build_object(
            'type', 'FeatureCollection',
            'features', COALESCE(jsonb_agg(ST_AsGeoJSON(sub.*)::jsonb), '[]'::jsonb)
        ) AS fc
        FROM (SELECT * FROM ({inner_sql}) q LIMIT {MAX_FEATURES}) sub
        """
    )
    engine = get_engine_readonly()
    async with engine.connect() as conn:
        fc = (await conn.execute(wrapped)).scalar_one()
    if isinstance(fc, str):
        fc = json.loads(fc)
    return fc, len(fc.get("features", []))


async def _resolve_city(city_id: int) -> str:
    try:
        engine = get_engine()
        async with engine.connect() as conn:
            row = (
                await conn.execute(
                    text("SELECT name, country FROM core.city WHERE id = :id"),
                    {"id": city_id},
                )
            ).fetchone()
        if row:
            return f"{row[0]}, {row[1]}" if row[1] else row[0]
    except Exception:  # noqa: BLE001
        pass
    return "the city"


# ---------------------------------------------------------------------------
async def run_nl_query(question: str, city_id: int = 1) -> dict:
    city = await _resolve_city(city_id)
    result: dict = {
        "ok": False,
        "city_id": city_id,
        "question": question,
        "is_clear": True,
        "task_type": None,
        "message": "",
        "answer": None,
        "count": 0,
        "sql": None,
        "explanation": None,
        "attempts": [],
    }

    # 1. Interpret
    try:
        intent = await _agent_interpret(question, city)
    except Exception as exc:  # noqa: BLE001
        result["message"] = f"Could not interpret the question: {exc}"
        return result
    result["task_type"] = intent.get("task_type")
    result["message"] = intent.get("message", "")
    if not intent.get("is_clear", False):
        result["is_clear"] = False
        return result  # follow-up question is in `message`

    # 2-4. Generate -> execute -> repair loop.
    # Repairs fire on a DB error, and once on a valid-but-empty result (the papers'
    # execution-review step). We keep the best successful attempt (prefer non-empty).
    prior_error: str | None = None
    empty_hint = False
    best: dict | None = None  # {sql, fc, count}
    for _ in range(MAX_REPAIRS + 2):
        try:
            sql = await _agent_generate(question, city_id, prior_error, empty_hint)
        except ValueError as exc:
            prior_error, empty_hint = str(exc), False
            result["attempts"].append({"sql": None, "error": str(exc)})
            continue
        try:
            fc, count = await _execute_to_geojson(sql, city_id)
        except Exception as exc:  # noqa: BLE001 - DB error text feeds the repair agent
            prior_error, empty_hint = str(exc).split("\n")[0][:400], False
            result["attempts"].append({"sql": sql, "error": prior_error})
            continue

        result["attempts"].append({"sql": sql, "rows": count})
        if best is None or count > best["count"]:
            best = {"sql": sql, "fc": fc, "count": count}
        if count > 0:
            break
        if not empty_hint:  # one loosening attempt for an empty result
            prior_error, empty_hint = None, True
            continue
        break

    if best is not None:
        result["ok"] = True
        result["sql"] = best["sql"]
        result["answer"] = best["fc"]
        result["count"] = best["count"]
    else:
        result["message"] = "I couldn't build a valid query for that. Try rephrasing."
        return result

    # 5. Explain
    try:
        result["explanation"] = await _agent_explain(
            question, result["sql"], result["answer"]["features"], result["count"], city
        )
    except Exception:  # noqa: BLE001
        result["explanation"] = f"Found {result['count']} matching features."

    return result
