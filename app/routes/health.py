"""Health / readiness checks, including PostGIS connectivity."""
from fastapi import APIRouter
from sqlalchemy import text

from app.db_spatial import get_engine

router = APIRouter()


@router.get("/health")
async def health():
    """Liveness + PostGIS readiness.

    Returns 200 even when the DB is down so the frontend can distinguish
    "backend up, DB down" from "backend unreachable". Inspect `db.ok`.
    """
    db_status = {"ok": False}
    try:
        engine = get_engine()
        async with engine.connect() as conn:
            version = (await conn.execute(text("SELECT postgis_full_version()"))).scalar_one()
            cities = (await conn.execute(text("SELECT count(*) FROM core.city"))).scalar_one()
            ready = (
                await conn.execute(
                    text("SELECT count(*) FROM core.city WHERE status = 'ready'")
                )
            ).scalar_one()
        db_status = {
            "ok": True,
            "postgis": version.split(" ")[0] if version else None,
            "cities": cities,
            "cities_ready": ready,
        }
    except Exception as exc:  # noqa: BLE001 - report any connection/setup failure verbatim
        db_status = {"ok": False, "error": str(exc)}

    return {"status": "ok", "service": "geoquery-sentinel", "db": db_status}
