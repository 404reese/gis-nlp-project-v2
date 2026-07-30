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
- Next: **M2** — the NL → PostGIS query engine (ask a spatial question, get a real answer layer).
