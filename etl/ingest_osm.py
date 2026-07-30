"""Ingest OpenStreetMap layers for a city via osmnx/Overpass.

Each function fetches a GeoDataFrame, stages it, then INSERT..SELECTs into the typed
target table with explicit geometry coercion. Generalizes to any city via the place
string (e.g. "Mumbai, India").
"""
from __future__ import annotations

import json
import time

import geopandas as gpd
import osmnx as ox
import pandas as pd
import requests
from shapely.geometry import shape
from sqlalchemy import text

from etl.db import delete_city_rows, exec_sql, stage_gdf

ox.settings.log_console = False
ox.settings.requests_timeout = 300

NOMINATIM = "https://nominatim.openstreetmap.org/search"


def resolve_city_polygon(engine, place: str, city_id: int):
    """Resolve a city's (Multi)Polygon boundary, generalizably.

    osmnx's geocode_to_gdf often returns a point for a bare city name, so we query
    Nominatim directly with polygon_geojson and take the first real polygon. Falls
    back to the city's seeded bbox so ingestion never hard-blocks on geocoding.
    """
    try:
        r = requests.get(
            NOMINATIM,
            params={"q": place, "format": "jsonv2", "polygon_geojson": 1, "limit": 5},
            headers={"User-Agent": "GeoQuerySentinel/0.1 (academic project)"},
            timeout=60,
        )
        time.sleep(1.1)
        for res in r.json():
            gj = res.get("geojson", {})
            if gj.get("type") in ("Polygon", "MultiPolygon"):
                print(f"    boundary: Nominatim polygon '{res.get('display_name', '')[:50]}'")
                return shape(gj)
    except Exception as exc:  # noqa: BLE001
        print(f"    boundary: Nominatim lookup failed ({exc})")

    with engine.begin() as conn:
        wkt = conn.execute(
            text("SELECT ST_AsText(bbox) FROM core.city WHERE id = :id"), {"id": city_id}
        ).scalar_one_or_none()
    if wkt:
        from shapely import wkt as shapely_wkt

        print("    boundary: falling back to seeded bbox")
        return shapely_wkt.loads(wkt)
    raise RuntimeError(f"Could not resolve a polygon for '{place}'")

# Curated POI categories (keeps the Overpass payload sane vs. "everything").
POI_TAGS = {
    "amenity": [
        "restaurant", "cafe", "fast_food", "bar", "bank", "atm", "hospital",
        "clinic", "doctors", "pharmacy", "school", "college", "university",
        "police", "fire_station", "fuel", "marketplace", "cinema", "place_of_worship",
    ],
    "shop": True,
    "tourism": ["hotel", "museum", "attraction"],
}
# Only these OSM tag keys are preserved into the tags jsonb (avoids 200-column bloat).
POI_TAG_KEYS = [
    "amenity", "shop", "tourism", "cuisine", "brand", "opening_hours",
    "phone", "website", "addr:street", "healthcare",
]

TRANSIT_TAGS = {
    "railway": ["station", "halt", "tram_stop"],
    "highway": "bus_stop",
    "station": ["subway"],
}

ROAD_FILTER = '["highway"~"motorway|trunk|primary|secondary|tertiary"]'


def _first(v):
    """OSM values are sometimes lists; take the first meaningful scalar."""
    if isinstance(v, list):
        return v[0] if v else None
    return v


def _tags_json(row, keys) -> str:
    out = {}
    for k in keys:
        if k in row:
            v = _first(row[k])
            if v is not None and not (isinstance(v, float) and pd.isna(v)):
                out[k] = str(v)
    return json.dumps(out, ensure_ascii=False)


# ---------------------------------------------------------------------------
def ingest_boundaries(engine, city_id: int, name: str, poly) -> int:
    """Store the resolved city outline + update core.city bbox/centroid from it."""
    gdf = gpd.GeoDataFrame({"geometry": [poly]}, crs="EPSG:4326")
    gdf["city_id"] = city_id
    gdf["name"] = name
    gdf["admin_level"] = None
    gdf["kind"] = "city"
    stage_gdf(gdf, engine, "admin_boundary")

    delete_city_rows(engine, "admin.boundary", city_id)
    exec_sql(
        engine,
        """
        INSERT INTO admin.boundary (city_id, name, admin_level, kind, geom)
        SELECT city_id, name, admin_level::int, kind,
               ST_Multi(ST_MakeValid(geom))::geometry(MultiPolygon, 4326)
        FROM staging.admin_boundary
        WHERE ST_Dimension(geom) = 2
        """,
    )
    exec_sql(
        engine,
        """
        UPDATE core.city c SET bbox = sub.bbox, centroid = sub.cent
        FROM (
            SELECT ST_Envelope(ST_Collect(geom))::geometry(Polygon, 4326) AS bbox,
                   ST_Centroid(ST_Collect(geom)) AS cent
            FROM admin.boundary WHERE city_id = :cid
        ) sub
        WHERE c.id = :cid
        """,
        {"cid": city_id},
    )
    return 1


def ingest_wards(engine, city_id: int, poly) -> int:
    """Administrative sub-divisions (best-effort; not all cities tag them)."""
    try:
        w = ox.features_from_polygon(
            poly, tags={"boundary": "administrative", "admin_level": ["8", "9"]}
        )
    except Exception as exc:  # noqa: BLE001
        print(f"    wards: none ({exc})")
        return 0
    w = w[w.geometry.type.isin(["Polygon", "MultiPolygon"])].reset_index()
    if w.empty:
        return 0
    g = gpd.GeoDataFrame(
        {
            "city_id": city_id,
            "name": w["name"] if "name" in w.columns else None,
            "admin_level": pd.to_numeric(w.get("admin_level"), errors="coerce"),
            "kind": "ward",
            "geometry": w.geometry,
        },
        crs=w.crs,
    )
    stage_gdf(g, engine, "admin_ward")
    exec_sql(
        engine,
        """
        INSERT INTO admin.boundary (city_id, name, admin_level, kind, geom)
        SELECT city_id, name, admin_level::int, kind,
               ST_Multi(ST_MakeValid(geom))::geometry(MultiPolygon, 4326)
        FROM staging.admin_ward WHERE ST_Dimension(geom) = 2
        """,
    )
    return len(g)


def ingest_roads(engine, city_id: int, poly) -> int:
    G = ox.graph_from_polygon(
        poly, custom_filter=ROAD_FILTER, simplify=True, retain_all=True
    )
    edges = ox.graph_to_gdfs(G, nodes=False).reset_index()
    edges["highway_class"] = edges["highway"].map(_first).astype(str)
    edges["rname"] = edges["name"].map(_first) if "name" in edges.columns else None
    edges["maxspeed_i"] = (
        pd.to_numeric(edges["maxspeed"].map(_first), errors="coerce")
        if "maxspeed" in edges.columns else None
    )
    edges["oneway_b"] = (
        edges["oneway"].map(lambda v: _first(v) in (True, "yes", "true"))
        if "oneway" in edges.columns else False
    )
    g = gpd.GeoDataFrame(
        {
            "city_id": city_id,
            "name": edges["rname"],
            "highway_class": edges["highway_class"],
            "maxspeed": edges["maxspeed_i"],
            "oneway": edges["oneway_b"],
            "geometry": edges.geometry,
        },
        crs=edges.crs,
    )
    stage_gdf(g, engine, "roads_segment")
    delete_city_rows(engine, "roads.segment", city_id)
    exec_sql(
        engine,
        """
        INSERT INTO roads.segment (city_id, name, highway_class, maxspeed, oneway, geom)
        SELECT city_id, name, highway_class,
               NULLIF(maxspeed, 'NaN')::double precision::int, oneway,
               (ST_Dump(geom)).geom::geometry(LineString, 4326)
        FROM staging.roads_segment
        WHERE GeometryType(geom) IN ('LINESTRING', 'MULTILINESTRING')
        """,
    )
    return len(g)


def ingest_transit(engine, city_id: int, poly) -> int:
    try:
        gdf = ox.features_from_polygon(poly, tags=TRANSIT_TAGS).reset_index()
    except Exception as exc:  # noqa: BLE001
        print(f"    transit: none ({exc})")
        return 0
    if gdf.empty:
        return 0

    def mode(r):
        rw = _first(r.get("railway"))
        st = _first(r.get("station"))
        if st == "subway" or rw == "subway":
            return "metro"
        if rw in ("station", "halt"):
            return "rail"
        if rw == "tram_stop":
            return "tram"
        if _first(r.get("highway")) == "bus_stop":
            return "bus"
        return "other"

    gdf["mode_"] = gdf.apply(mode, axis=1)
    gdf["name_"] = gdf["name"] if "name" in gdf.columns else None
    g = gpd.GeoDataFrame(
        {"city_id": city_id, "name": gdf["name_"], "mode": gdf["mode_"], "geometry": gdf.geometry},
        crs=gdf.crs,
    )
    stage_gdf(g, engine, "transport_stop")
    delete_city_rows(engine, "transport.stop", city_id)
    exec_sql(
        engine,
        """
        INSERT INTO transport.stop (city_id, name, mode, geom)
        SELECT city_id, name, mode,
               ST_Centroid(ST_MakeValid(geom))::geometry(Point, 4326)
        FROM staging.transport_stop
        """,
    )
    return len(g)


def ingest_pois(engine, city_id: int, poly) -> int:
    gdf = ox.features_from_polygon(poly, tags=POI_TAGS).reset_index()
    if gdf.empty:
        return 0

    def category(r):
        for k in ("amenity", "tourism"):
            v = _first(r.get(k))
            if v is not None and not (isinstance(v, float) and pd.isna(v)):
                return str(v)
        s = _first(r.get("shop"))
        if s is not None and not (isinstance(s, float) and pd.isna(s)):
            return "shop"
        return "other"

    gdf["category_"] = gdf.apply(category, axis=1)
    gdf["name_"] = gdf["name"] if "name" in gdf.columns else None
    gdf["tags_"] = gdf.apply(lambda r: _tags_json(r, POI_TAG_KEYS), axis=1)
    g = gpd.GeoDataFrame(
        {
            "city_id": city_id,
            "name": gdf["name_"],
            "category": gdf["category_"],
            "tags": gdf["tags_"],
            "geometry": gdf.geometry,
        },
        crs=gdf.crs,
    )
    stage_gdf(g, engine, "poi_place")
    delete_city_rows(engine, "poi.place", city_id)
    exec_sql(
        engine,
        """
        INSERT INTO poi.place (city_id, name, category, tags, geom)
        SELECT city_id, name, category, tags::jsonb,
               ST_Centroid(ST_MakeValid(geom))::geometry(Point, 4326)
        FROM staging.poi_place
        """,
    )
    return len(g)
