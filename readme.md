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
- **M0 — Foundations: scaffolded.** PostGIS+pgvector via Docker, Martin tiles, DB schema,
  FastAPI `/health`, MapLibre studio shell.
- Next: **M1** — real Mumbai data layers (admin, roads, POIs, real-estate) via ETL.
