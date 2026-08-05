# GeoQuery Sentinel

Natural-language → spatial-query mapping platform (a "Felt-like" layered map driven by
an NL→PostGIS engine). See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full plan
and [docs/RUNBOOK.md](docs/RUNBOOK.md) to run it locally.

## Quick start
```bash
docker compose up -d --build      # PostGIS + Martin
pip install -r app/requirements.txt && uvicorn app.main:app --reload   # backend :8000
cd frontend && npm install && npm run dev                              # frontend :3000
```
Then open http://localhost:3000/studio · health check http://localhost:8000/health

## Status
- **M0 — Foundations: done.** PostGIS+pgvector via Docker, Martin tiles, DB schema,
  FastAPI `/health`, MapLibre studio shell.
- **M1 — Real Mumbai layers: done.** ETL (`etl/`) loads live OSM data + real-estate + crime
  into PostGIS; Studio shows toggleable, styled vector-tile layers with legends.
  Current Mumbai load: 48 admin boundaries, 16.8k roads, 2.2k transit stops, 10.8k POIs,
  55.6k real-estate points, 40 crime areas.
- **M2 — NL → PostGIS engine: done.** Ask a plain-English spatial question in Studio →
  a multi-agent pipeline (intent → schema-grounded SQL → sandboxed execution → self-repair →
  explanation) returns a real GeoJSON answer layer, the explanation, and the SQL it ran.
  Endpoint: `POST /nlquery`. Runs as the read-only `geo_readonly` role.
  Try: *"hospitals within 1 km of a metro station"*, *"cafes in Bandra"*, *"cheapest 2 BHK flats"*,
  *"safest areas to live"*.
- Next: **M3** — Felt-grade UI polish (draw/measure, saved & shareable maps).
