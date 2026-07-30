"""ETL orchestrator.

Usage:
    python -m etl.run --city "Mumbai, India"
    python -m etl.run --city "Pune, India" --skip realestate,crime

Each layer runs independently; one failing layer does not abort the rest. The city's
status is set to 'ready' if the core layers loaded, else 'error'.
"""
from __future__ import annotations

import argparse
import traceback

from etl.catalog import seed_catalog
from etl.db import count, ensure_city, get_engine, set_city_status
from etl.ingest_crime import ingest_crime
from etl.ingest_osm import (
    ingest_boundaries,
    ingest_pois,
    ingest_roads,
    ingest_transit,
    ingest_wards,
    resolve_city_polygon,
)
from etl.ingest_realestate import ingest_realestate


def _run(label, fn, *args):
    print(f"[{label}] starting...")
    try:
        n = fn(*args)
        print(f"[{label}] done: {n} features")
        return n
    except Exception as exc:  # noqa: BLE001
        print(f"[{label}] FAILED: {exc}")
        traceback.print_exc()
        return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--city", default="Mumbai, India", help='e.g. "Mumbai, India"')
    ap.add_argument("--skip", default="", help="comma list: boundaries,wards,roads,transit,pois,realestate,crime")
    args = ap.parse_args()

    name = args.city.split(",")[0].strip()
    country = args.city.split(",")[-1].strip() if "," in args.city else ""
    skip = {s.strip() for s in args.skip.split(",") if s.strip()}

    engine = get_engine()
    city_id = ensure_city(engine, name, country)
    print(f"City '{name}, {country}' -> id={city_id}\n")

    # Resolve the city polygon once; every OSM layer is clipped to it.
    poly = resolve_city_polygon(engine, args.city, city_id)

    results = {}
    if "boundaries" not in skip:
        results["boundaries"] = _run("boundaries", ingest_boundaries, engine, city_id, name, poly)
    if "wards" not in skip:
        results["wards"] = _run("wards", ingest_wards, engine, city_id, poly)
    if "roads" not in skip:
        results["roads"] = _run("roads", ingest_roads, engine, city_id, poly)
    if "transit" not in skip:
        results["transit"] = _run("transit", ingest_transit, engine, city_id, poly)
    if "pois" not in skip:
        results["pois"] = _run("pois", ingest_pois, engine, city_id, poly)
    if "realestate" not in skip:
        results["realestate"] = _run("realestate", ingest_realestate, engine, city_id, name, country)
    if "crime" not in skip:
        results["crime"] = _run("crime", ingest_crime, engine, city_id)

    _run("catalog", seed_catalog, engine)

    core_ok = results.get("boundaries", 0) > 0 and (
        results.get("roads", 0) > 0 or results.get("pois", 0) > 0
    )
    set_city_status(engine, city_id, "ready" if core_ok else "error")

    print("\n=== Summary ===")
    for k in ("boundaries", "wards", "roads", "transit", "pois", "realestate", "crime"):
        if k in results:
            print(f"  {k:12s}: {results[k]}")
    print(f"  status      : {'ready' if core_ok else 'error'}")
    print("\nRestart Martin so it picks up any new tables:  docker restart geoquery-martin")


if __name__ == "__main__":
    main()
