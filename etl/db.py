"""Shared DB helpers for the ETL pipeline (sync SQLAlchemy, for geopandas.to_postgis)."""
from __future__ import annotations

import os

from sqlalchemy import create_engine, text

# Sync engine (psycopg2) — geopandas.to_postgis needs a sync SQLAlchemy engine.
# Defaults to the container's host port (5433). Override with ETL_DATABASE_URL.
ETL_DATABASE_URL = os.environ.get(
    "ETL_DATABASE_URL", "postgresql+psycopg2://geo:geo@localhost:5433/geo"
)


def get_engine():
    return create_engine(ETL_DATABASE_URL, future=True)


def ensure_city(engine, name: str, country: str) -> int:
    """Return the city_id, creating the row if needed (status -> ingesting)."""
    with engine.begin() as conn:
        row = conn.execute(
            text("SELECT id FROM core.city WHERE name = :n AND country = :c"),
            {"n": name, "c": country},
        ).fetchone()
        if row:
            conn.execute(
                text("UPDATE core.city SET status = 'ingesting' WHERE id = :id"),
                {"id": row[0]},
            )
            return row[0]
        return conn.execute(
            text(
                "INSERT INTO core.city (name, country, status) "
                "VALUES (:n, :c, 'ingesting') RETURNING id"
            ),
            {"n": name, "c": country},
        ).scalar_one()


def set_city_status(engine, city_id: int, status: str) -> None:
    with engine.begin() as conn:
        conn.execute(
            text("UPDATE core.city SET status = :s, ingested_at = now() WHERE id = :id"),
            {"s": status, "id": city_id},
        )


def delete_city_rows(engine, qualified_table: str, city_id: int) -> None:
    """Idempotency: clear a city's rows before re-inserting a layer."""
    with engine.begin() as conn:
        conn.execute(
            text(f"DELETE FROM {qualified_table} WHERE city_id = :id"), {"id": city_id}
        )


def stage_gdf(gdf, engine, table: str) -> int:
    """Write a GeoDataFrame to staging.<table> with geometry column 'geom'.

    Staging decouples pandas dtype quirks (lists, jsonb, mixed geom types) from the
    typed target schema; the caller then does an INSERT..SELECT with explicit casts.
    """
    gdf = gdf.copy()
    if gdf.geometry.name != "geom":
        gdf = gdf.rename_geometry("geom")
    with engine.begin() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS staging"))
    gdf.to_postgis(table, engine, schema="staging", if_exists="replace", index=False)
    return len(gdf)


def exec_sql(engine, sql: str, params: dict | None = None) -> int:
    with engine.begin() as conn:
        res = conn.execute(text(sql), params or {})
        return res.rowcount if res.rowcount is not None else 0


def count(engine, qualified_table: str, city_id: int) -> int:
    with engine.begin() as conn:
        return conn.execute(
            text(f"SELECT count(*) FROM {qualified_table} WHERE city_id = :id"),
            {"id": city_id},
        ).scalar_one()
