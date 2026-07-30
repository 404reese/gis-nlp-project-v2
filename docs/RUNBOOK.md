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
- Postgres/PostGIS → `localhost:5432` (user/pass/db all `geo`)
- Martin vector tiles → `localhost:3001`  (health: http://localhost:3001/health)

The DB init scripts in `db/init/` run **once**, on first startup with an empty data
volume. To re-apply them after editing, reset the volume:
```bash
docker compose down -v && docker compose up -d --build
```

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
