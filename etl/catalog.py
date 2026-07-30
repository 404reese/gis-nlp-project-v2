"""Seed meta.schema_catalog with human descriptions of every queryable column.

The NL->SQL engine (M2) retrieves relevant tables/columns from here to ground a query
against the real schema. Embeddings are added in M2; for now we store descriptions so
the catalog is queryable immediately.
"""
from __future__ import annotations

from sqlalchemy import text

# (schema, table, column, data_type, is_geometry, description)
CATALOG = [
    ("core", "city", "name", "text", False, "City name, e.g. Mumbai"),
    ("core", "city", "bbox", "geometry", True, "Bounding box polygon of the city"),
    ("admin", "boundary", "name", "text", False, "Administrative area name (city/ward)"),
    ("admin", "boundary", "kind", "text", False, "Boundary kind: city, ward, zone, district"),
    ("admin", "boundary", "geom", "geometry(MultiPolygon)", True, "Administrative boundary polygon"),
    ("roads", "segment", "name", "text", False, "Road/street name"),
    ("roads", "segment", "highway_class", "text", False, "Road class: motorway, trunk, primary, secondary, tertiary"),
    ("roads", "segment", "maxspeed", "int", False, "Speed limit in km/h"),
    ("roads", "segment", "geom", "geometry(LineString)", True, "Road centerline geometry"),
    ("transport", "stop", "name", "text", False, "Transit stop/station name"),
    ("transport", "stop", "mode", "text", False, "Transit mode: bus, metro, rail, tram"),
    ("transport", "stop", "geom", "geometry(Point)", True, "Transit stop location"),
    ("poi", "place", "name", "text", False, "Point-of-interest name"),
    ("poi", "place", "category", "text", False, "POI category: restaurant, cafe, bank, hospital, clinic, pharmacy, school, shop, hotel, place_of_worship, etc."),
    ("poi", "place", "tags", "jsonb", False, "Raw OSM tags (cuisine, brand, opening_hours, address...)"),
    ("poi", "place", "geom", "geometry(Point)", True, "POI location"),
    ("realestate", "listing", "locality", "text", False, "Locality/neighbourhood of the property"),
    ("realestate", "listing", "bhk", "int", False, "Number of bedrooms (BHK)"),
    ("realestate", "listing", "price", "double precision", False, "Listed price (see price_unit: Cr=crore, L=lakh)"),
    ("realestate", "listing", "price_unit", "text", False, "Price unit: Cr (crore) or L (lakh)"),
    ("realestate", "listing", "area_sqft", "double precision", False, "Carpet/built-up area in square feet"),
    ("realestate", "listing", "geom", "geometry(Point)", True, "Approximate property location (region-level)"),
    ("demo", "cell", "population", "double precision", False, "Population count in the cell/ward"),
    ("demo", "cell", "density", "double precision", False, "Population density"),
    ("demo", "cell", "income_index", "double precision", False, "Relative income index"),
    ("demo", "cell", "geom", "geometry(Polygon)", True, "Demographic cell/ward polygon"),
    ("crime", "area", "name", "text", False, "Area name for the safety score"),
    ("crime", "area", "safety_score", "int", False, "Safety score 0-100 (higher is safer)"),
    ("crime", "area", "risk_level", "text", False, "Risk level: low, medium, high"),
    ("crime", "area", "breakdown", "jsonb", False, "Per-category crime counts (ndps, cyber, fraud, drugs...)"),
    ("crime", "area", "geom", "geometry(Point)", True, "Area location for the safety score"),
    ("env", "measurement", "kind", "text", False, "Measurement kind: aqi, flood_risk"),
    ("env", "measurement", "value", "double precision", False, "Measured value (AQI index or flood risk score)"),
    ("env", "measurement", "geom", "geometry", True, "Measurement location or zone"),
]


def seed_catalog(engine) -> int:
    with engine.begin() as conn:
        for schema, table, column, dtype, is_geom, desc in CATALOG:
            conn.execute(
                text(
                    """
                    INSERT INTO meta.schema_catalog
                        (schema_name, table_name, column_name, data_type, is_geometry, description)
                    VALUES (:s, :t, :c, :d, :g, :desc)
                    ON CONFLICT (schema_name, table_name, column_name)
                    DO UPDATE SET data_type = EXCLUDED.data_type,
                                  is_geometry = EXCLUDED.is_geometry,
                                  description = EXCLUDED.description
                    """
                ),
                {"s": schema, "t": table, "c": column, "d": dtype, "g": is_geom, "desc": desc},
            )
    return len(CATALOG)
