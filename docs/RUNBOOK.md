# Runbook — local development

## Prerequisites
- Docker Desktop (running)
- Python env for the backend (venv/conda) with `pip install -r app/requirements.txt`
- Node 20+ for the frontend

## 1. Infrastructure (PostGIS + Martin)
```bash
cp .env.example .env            # adjust if desired
docker compose up -d --build    # first run builds the postgis+pgvector image
```
- Postgres/PostGIS → `localhost:5433` (host port 5433 avoids a native Postgres on 5432; user/pass/db all `geo`)
- Martin vector tiles → `localhost:3001`  (catalog: http://localhost:3001/catalog)

The DB init scripts in `db/init/` run **once**, on first startup with an empty data
volume. To re-apply them after editing, reset the volume:
```bash
docker compose down -v && docker compose up -d --build
```

## 1.5 Load real data (ETL — any city)
```bash
pip install -r etl/requirements.txt         # osmnx, geopandas, ... (heavier)
python -m etl.run --city "Mumbai, India"    # OSM + real-estate + crime -> PostGIS
docker restart geoquery-martin              # pick up any newly created tables
```
Ingests admin boundaries, roads, transit, POIs (OSM), geocodes the house-price CSV into
a real-estate layer, and loads the crime dataset. Re-runnable (idempotent per city).
Any city works: `python -m etl.run --city "Pune, India"`.

## 2. Backend (FastAPI)
```bash
pip install -r app/requirements.txt
uvicorn app.main:app --reload
```
- API → `localhost:8000`
- Health + PostGIS check → http://localhost:8000/health
  (`db.ok:true` means the app reached PostGIS; `cities` should be ≥ 1 after seed.)

## 3. Frontend (React + MapLibre)
```bash
cd frontend
cp .env.example .env.local      # add VITE_MAPTILER_KEY for nicer basemaps (optional)
npm install
npm run dev
```
- App → `localhost:3000`
- Studio (the new Felt-like map) → http://localhost:3000/studio

## Notes
- Without a MapTiler key the map falls back to the free MapLibre demo style.
- Data layers are empty until the M1 ETL pipeline lands (`etl/`).
