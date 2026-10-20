# Agent Instructions: GeoQuery Sentinel

## 1. Project Context & Stack
- **Purpose:** Felt-style layered web map driven by a natural-language → PostGIS query engine. Grounded in real open data (OSM, Mumbai house prices, crime). Designed to work for any city; Mumbai is the pre-loaded one (`city_id=1`).
- **Domain:** GIS, NL2SQL, real-estate site evaluation, business cost estimation. It is also an academic major project with a research paper (`paper-publication/`).
- **Backend:** Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2 async + asyncpg, GeoAlchemy2.
- **DB:** PostgreSQL 16 + PostGIS 3.4 + pgvector (Docker). MongoDB holds chat history only.
- **Tiles:** Martin v0.14 serves MVT straight from PostGIS.
- **LLM:** Groq, called only through `app/services/groq_client.py`. Model: `openai/gpt-oss-120b`.
- **Frontend:** React 19 + Vite 8, MapLibre GL 4, Zustand 5, axios, react-router 7. Plain JS/JSX (one legacy `.tsx`).
- **ETL:** osmnx + geopandas (`etl/`).
- **Paper:** Typst (`.typ`) + BibTeX.

## 2. Source Code Architecture
- `app/main.py`: FastAPI app, router registration, lifespan.
- `app/config.py`: `Settings` (reads `app/.env`). `app/db_spatial.py`: lazy `get_engine()` (owner) / `get_engine_readonly()` (LLM SQL, 15 s timeout).
- `app/routes/*.py`: thin `APIRouter` modules. Request models go in the route file, logic goes in services.
  - **Current:** `health`, `nlquery`, `site`, `business`, `competition`.
  - **Legacy POC:** `analyze`, `generate`, `explain`, `query`, `location_insight`, `properties`.
- `app/services/geo_engine.py`: NL engine with the stages interpret → schema-grounded SQL-gen → `validate_select` → execute as `geo_readonly` → repair → explain.
- `app/services/{site_evaluator,business_estimator,competitor_analysis}.py`: M3 real-estate suite.
- `db/init/0X_*.sql`: extensions, schema (`core, admin, roads, transport, poi, realestate, demo, crime, env, meta`), roles, seed. These run **only on first volume init**.
- `etl/run.py`: per-city idempotent ingest. `etl/catalog.py` writes `meta.schema_catalog`, which grounds the LLM.
- `martin/config.yaml`: tile sources published as `schema.table`.
- `frontend/src/pages/Studio.jsx`: main map. `components/` holds the panels and `NLQueryBar.jsx`, `MapCanvas.jsx`, `VectorLayers.jsx`.
- `frontend/src/config/layers.js` (LAYER_DEFS), `store/mapStore.js` (Zustand), `services/api.js` (every HTTP call).
- `eval/nl2sql/`: benchmark (`questions.py` gold SQL, `run_benchmark.py`). `eval/weight_study.py`: scoring-weight study. Outputs go to `eval/results/`.
- `docs/ARCHITECTURE.md` (design source of truth), `docs/RUNBOOK.md` (run steps).

## 3. Developer Workflows & Commands
Infra (Docker Desktop must be running):
```bash
cp .env.example .env
docker compose up -d --build            # PostGIS on localhost:5433, Martin on localhost:3001
docker compose down -v && docker compose up -d --build   # ONLY to re-apply db/init (wipes data)
docker restart geoquery-martin          # after ETL creates new tables
```
ETL:
```bash
pip install -r etl/requirements.txt
python -m etl.run --city "Mumbai, India"
```
Backend (use the repo venv; global Python has no FastAPI):
```bash
app\venv\Scripts\python -m pip install -r app/requirements.txt
app\venv\Scripts\python -m uvicorn app.main:app --reload --port 8000   # health: /health
app\venv\Scripts\python -m py_compile app/services/<file>.py          # minimum check
```
Frontend:
```bash
cd frontend && npm install
npm run dev      # http://localhost:3000/studio
npm run lint
npm run build    # must pass before you declare the frontend done
```
Eval:
```bash
app\venv\Scripts\python eval\nl2sql\run_benchmark.py --lint            # no DB, no LLM
app\venv\Scripts\python eval\nl2sql\run_benchmark.py --validate-gold   # DB, no LLM
app\venv\Scripts\python eval\nl2sql\run_benchmark.py --limit 3 --configs full   # smoke test
```
Everything at once: `start.bat` / `stop.bat`.

## 4. Coding Standards & Conventions
- **Python:** type hints on every function signature, `from __future__ import annotations` in new modules, `async def` for anything that touches the DB.
- **DB access:** `sqlalchemy.text()` with **bound parameters** only. Never build SQL values with f-strings.
- **Engines:** get them from `app.db_spatial`. Never call `create_async_engine` anywhere else.
- **Boot without dependencies:** the app MUST start when Postgres or Groq is down. Endpoints report the failure and never crash at import.
- **LLM calls:** go through `groq_client`. Every LLM-backed feature needs a deterministic heuristic fallback (see `business_estimator`).
- **Grounding:** numbers shown to users (prices, distances, counts, scores) come from SQL over real tables. The LLM explains and itemises; it never makes up places, coordinates or metrics.
- **Schema facts:**
  - `crime.area` doubles as the neighbourhood gazetteer, because OSM wards are named like `'K/W Ward'`.
  - `poi.place` is the only amenity table.
  - `transport.stop.mode` ∈ {bus, metro, rail, tram}.
  - Geometry is SRID 4326. Cast to `geography` for distances in metres.
- **Schema changes:** add a new numbered `db/init/` file or an ETL step, update `etl/catalog.py` so the LLM sees the change, and grant SELECT to `geo_readonly`.
- **New endpoint:** route file in `app/routes/`, service in `app/services/`, `include_router` in `main.py`, client function in `frontend/src/services/api.js`.
- **Frontend:**
  - Functional components and hooks only.
  - Shared map state lives in `mapStore`, not in prop chains.
  - New map layers are added to `LAYER_DEFS`.
  - Use MapLibre for new map work. Leaflet is legacy POC code.
  - No Tailwind CDN. Use plain CSS.
- **Style:** match the surrounding code. Keep comments sparse and about *why*. Make small focused diffs.

## 5. Critical Constraints
- NEVER run LLM-generated SQL on the owner engine. Use `get_engine_readonly()` after `validate_select()`, and keep both.
- NEVER loosen `validate_select`, the `geo_readonly` grants, or the statement timeout.
- NEVER run `docker compose down -v` or drop tables/schemas without explicit user approval, because it destroys ETL data that takes a long time to rebuild.
- NEVER change port 5433 back to 5432. A native PostgreSQL 18 already uses 5432 on this machine.
- NEVER commit secrets (`.env`, `app/.env`, `GROQ_API_KEY`), `__pycache__/`, `app/venv/`, `node_modules/`, `.pnpm-store/`, or `cache/`.
- NEVER edit or delete `eval/results/<timestamp>/` runs. They are paper evidence. Write new runs to new folders.
- NEVER edit `eval/nl2sql/questions.py` gold SQL to make the engine score higher.
- NEVER change the LLM model, prompts in `geo_engine.py`, or scoring weights without saying so. They change the published results.
- NEVER install packages globally or switch package managers. Frontend uses `npm` (`package-lock.json`).
- NEVER run full benchmarks (`--runs 3`) unprompted. They burn the Groq free-tier quota, so use `--limit` and `--sleep`.
- There is no automated test suite. Do not invent `pytest`/`npm test` runs. Verify with `py_compile`, `npm run build`, `/health`, and a real HTTP call.
- If one command fails twice the same way, stop and report it instead of retrying variants. Usual causes: Docker not running, the wrong Python, or an empty DB that needs ETL.
