# GeoQuery Sentinel — Architecture & Build Plan

> Turning the POC into a "proper" product: a **Felt-like layered map** driven by a
> **natural-language → spatial-query engine**, backed by **PostGIS + real open data**,
> generalizable to **any city**.

Status: **APPROVED. M0 + M1 + M2 done** (foundations · real Mumbai layers · NL→PostGIS engine).
Next: M3 (Felt-grade UI: draw/measure, saved & shareable maps). See §8 roadmap and docs/RUNBOOK.md.
Last updated: 2026-07-30.

---

## 1. Vision

Two reference points define "proper":

1. **Felt.com** — the *product* bar. Real vector geodata, a composable **layer system**
   (toggle / reorder / opacity / style / legend), drawing & measuring tools, upload your
   own data, shareable saved maps. Crisp vector basemaps, not raster markers.

2. **The papers** — the *research* bar. The core novelty is replacing "LLM hallucinates
   answers" with **NL → structured spatial query → real spatial computation on real data**:

   | Paper | What we take from it |
   |---|---|
   | *Spatial Text-to-SQL, multi-agent* (arXiv 2510.21045) | The engine: 5-stage agent pipeline — intent → schema grounding → logical plan → SQL generation → **execution-based review/correction**. Embedding retrieval over schema metadata. |
   | *ChatGeoAI* (MDPI ISPRS IJGI 13(10):348) | NL → **executable geospatial operations** (buffer, proximity, spatial join, isochrone) for the public, not just SQL. |
   | *GeoLLM* (arXiv 2310.06213, ICLR'24) | Fuse **LLM knowledge + OSM features** to *predict* metrics where ground-truth data is missing (e.g. footfall proxy). |
   | *NL↔GIS multi-agent frameworks* (IEEE / IJDE 2278895) | Autonomous decomposition of a geospatial task across specialized agents; validation loops. |

**One-line thesis:** *"Ask any spatial question about any city in plain English; the system
grounds it against real data layers, composes and runs a validated PostGIS query, and renders
the result as a styled, explainable map layer."*

---

## 2. Where the POC stands today (honest baseline)

**Backend (FastAPI + Groq llama-3.3-70b)**
- `/analyze → /generate → /explain`: the LLM **invents the areas *and their lat/lon*** — hallucination risk — then enriches from a local file.
- `/query` (Mongo-persisted chat) → `rank_locations`: a **fixed weighted formula** over ~40 hardcoded Mumbai areas with synthetic 1–10 metrics.
- `/properties`: the one genuinely real dataset — 76k-row Mumbai house-price CSV.
- `crime.json`: rich per-area/zone crime data (real-ish).

**Frontend (React 19 + Leaflet raster + Tailwind Play CDN)**
- Three uncoordinated Leaflet maps; **marker coordinates are random jitter** in two places
  (`MapView.jsx:146`, `LocationDetailPanel.jsx:281`).
- Heatmap over 7 synthetic factors; **no polygons, no vector tiles, no layer panel, no drawing.**
- Tailwind via **dev-only CDN** (not production-safe); dead `App.css`; hardcoded API base.

**Verdict:** great demo skeleton, but the "GIS" is synthetic and the "spatial" is a scoring
formula. The rebuild keeps the good UX bones and replaces the fake core with a real one.

---

## 3. Target architecture

```
                        ┌─────────────────────────────────────────────┐
   City name / bbox ──► │  INGESTION (per-city, on demand + cached)    │
                        │  osmnx/Overpass · WorldPop/GHSL · OpenAQ ·   │
                        │  Nominatim geocoder · house-price CSV        │
                        └───────────────────┬─────────────────────────┘
                                            ▼
                        ┌─────────────────────────────────────────────┐
                        │  PostGIS  (PostgreSQL 16 + PostGIS 3.4 +     │
                        │  pgvector)  — one schema per layer group     │
                        │  + `schema_catalog` (table/column metadata + │
                        │    embeddings for retrieval)                 │
                        └───────────────────┬─────────────────────────┘
                                            ▼
   NL question ─► ┌──────────────────────────────────────────────────┐
                  │  NL → SPATIAL QUERY ENGINE (multi-agent)          │
                  │  1 Intent  2 Schema-ground  3 Plan  4 SQL         │
                  │  5 Execute + self-correct  (+ GeoLLM fallback)    │
                  └───────────────────┬──────────────────────────────┘
                                      ▼
                  ┌──────────────────────────────────────────────────┐
                  │  FastAPI:  /geocode /layers /nlquery /tiles       │
                  │  vector tiles via Martin/pg_tileserv (MVT)        │
                  └───────────────────┬──────────────────────────────┘
                                      ▼
                  ┌──────────────────────────────────────────────────┐
                  │  FRONTEND (React + MapLibre GL vector)            │
                  │  Layer panel · legends · draw/measure · NL bar ·  │
                  │  styling · saved/shareable maps · data upload     │
                  └──────────────────────────────────────────────────┘
```

### 3.1 Technology choices (concrete)

| Concern | Choice | Why |
|---|---|---|
| Spatial DB | **PostgreSQL 16 + PostGIS 3.4**, `pgvector`, `postgis_raster` | Industry standard; matches the Text-to-SQL papers directly. `pgvector` powers schema-embedding retrieval. |
| DB delivery | **Docker Compose** (`postgis/postgis:16-3.4`) | Zero-pain install on Windows 11; reproducible for a defense/demo. |
| Vector tiles | **Martin** (or `pg_tileserv`) | Serves MVT straight from PostGIS → Felt-grade vector rendering, no manual tiling. |
| ETL | **Python**: `osmnx`, `overpass`, `geopandas`, `shapely`, `pyproj`, `requests`, `geoalchemy2` | The generalizable "any city" pipeline. |
| Backend | **FastAPI** (keep) + `asyncpg`/SQLAlchemy 2 + GeoAlchemy2 | Reuse current app; add spatial layer. |
| LLM | **Groq llama-3.3-70b** (keep), abstracted behind a provider interface | Cheap/fast for the agent loop; swappable for a stronger model on the SQL-gen step. |
| Frontend map | **MapLibre GL JS** (replace Leaflet) | Vector tiles, styled basemaps, expressions-based theming = the Felt look. `deck.gl` optional for heavy layers. |
| Frontend build | **Local Tailwind + Vite** (kill the CDN) | Production-safe, purged, dark-mode fixed. |
| Geocoding | **Nominatim** (self-host later) | Free, any city; resolves "Mumbai", localities, addresses → coords/bbox. |

---

## 4. Data model — PostGIS schema per layer group

All geometries stored in **EPSG:4326**, with generated `geometry(..., 3857)` mirrors or
`ST_Transform` at query time for metric ops; every table has a GiST spatial index. Every
city's data is tagged with a `city_id` so one DB serves many cities.

```
core.city(id, name, country, centroid geometry(Point,4326), bbox geometry(Polygon,4326), ingested_at)

-- Administrative + Roads/Transport
admin.boundary(id, city_id, name, admin_level, kind, geom geometry(MultiPolygon,4326))   -- ward/zone/city
roads.segment(id, city_id, name, highway_class, maxspeed, oneway, geom geometry(LineString,4326))
transport.stop(id, city_id, name, mode /*bus|metro|rail*/, geom geometry(Point,4326))
transport.line(id, city_id, name, mode, geom geometry(LineString,4326))

-- Businesses/POIs + Real Estate
poi.place(id, city_id, name, category /*restaurant|bank|hospital|store|...*/, tags jsonb, geom geometry(Point,4326))
realestate.listing(id, city_id, locality, bhk, type, area_sqft, price, price_unit, status, age,
                   geom geometry(Point,4326))     -- current CSV, geocoded per locality

-- Population/Demographics
demo.cell(id, city_id, population, density, age_median, income_index, source, geom geometry(Polygon,4326))  -- grid/ward

-- Crime + Environment
crime.incident_agg(id, city_id, zone, category, count, period, geom geometry(MultiPolygon,4326))  -- from crime.json
env.measurement(id, city_id, kind /*aqi|flood_risk*/, value, ts, geom geometry(Point|Polygon,4326))

-- Text-to-SQL grounding
meta.schema_catalog(table_name, column_name, data_type, is_geometry, description, embedding vector(768))
```

**Migration of existing assets**
- `Mumbai House Prices.csv` → `realestate.listing` (geocode the ~unique localities once, cache).
- `crime.json` per-area + per-zone → `crime.incident_agg` (+ optional zone polygons).
- `dataset.json` synthetic metrics → **retired** as ground truth; kept only as an optional
  "curated demo" overlay. Real footfall/youth become **GeoLLM-predicted** proxies (§5.4).

---

## 5. The NL → Spatial Query engine (the research core)

A **multi-agent pipeline** (arXiv 2510.21045 + ChatGeoAI), each stage a focused LLM call with
strict JSON I/O and a repair loop.

```
NL query ─► [1 Intent] ─► [2 Schema Grounding] ─► [3 Logical Plan] ─► [4 SQL Gen] ─► [5 Execute+Review] ─► GeoJSON + explanation
                                    ▲                                                        │ (on error/empty)
                                    └───────────────── retrieval (pgvector) ◄───────────────┘
```

1. **Intent** — classify task type (site-selection · proximity · filter · aggregation ·
   routing/isochrone · risk overlay), extract entities (place, category, constraints,
   thresholds, target metric). Ask a follow-up if underspecified (keeps the current
   `is_clear` behavior, but structured).
2. **Schema grounding** — embed the intent, retrieve the top-K relevant tables/columns from
   `meta.schema_catalog` via `pgvector`. Disambiguate ("hospital" → `poi.place WHERE
   category='hospital'`). This is the paper's key move against schema ambiguity.
3. **Logical plan** — a DB-agnostic plan: sources, spatial predicates (`within`, `dwithin`,
   `intersects`), joins, buffers/isochrones, scoring/weights, ordering, limit.
4. **SQL generation** — plan → **parameterized PostGIS SQL** (ST_DWithin, ST_Buffer,
   ST_Intersects, KNN `<->`, ST_Transform for metric distance). Whitelist tables/functions;
   read-only role; statement timeout.
5. **Execute + review** — run it; if it errors or returns empty/implausible, feed the DB error
   + row count back for **self-correction** (the paper's +11pt "reviewer" stage). Cap retries.

**Outputs:** a GeoJSON `FeatureCollection` (the answer layer) + a natural-language explanation
(reuses `/explain`, now grounded in *real* returned rows, not vibes) + the SQL (shown in a
"how this was computed" panel — great for a defense).

### 5.4 GeoLLM fallback for missing metrics
Where a real layer doesn't exist (footfall, "youth vibe", brand visibility), don't hallucinate a
number — compute a **feature vector from OSM** (nearby POI counts by category, road density,
transit access) and let the LLM score it *from features* (GeoLLM). The score is then defensible
and reproducible, and clearly labeled "modeled, not measured."

### 5.5 Safety & correctness guardrails
- Dedicated **read-only** DB role; SQL restricted to a table/function allowlist; `statement_timeout`.
- All user input parameterized; the LLM never string-concats values into SQL.
- Every answer carries provenance: source, query, and modeled-vs-measured flags.

---

## 6. Backend API (redesign)

Keep FastAPI; evolve the routes.

| Endpoint | Purpose |
|---|---|
| `POST /cities/resolve` | Geocode a city name → `city_id`, bbox, centroid (Nominatim). |
| `POST /cities/{id}/ingest` | Kick off (async) ingestion of selected layers for a city. |
| `GET /cities/{id}/layers` | List available layers + metadata + legend spec. |
| `POST /nlquery` | **The engine** (§5). Body: `{city_id, question, chat_id?}` → `{answer_layer(GeoJSON), explanation, sql, plan}`. |
| `GET /tiles/{layer}/{z}/{x}/{y}.pbf` | MVT vector tiles (via Martin) for base layers. |
| `POST /explain` | Grounded explanation of a result set (kept, upgraded). |
| `GET /realestate?bbox=&bhk=&price_max=` | Real-estate points (replaces `/properties`, now spatial). |

Existing `/analyze`, `/generate`, `/location-insight`, Mongo chat history → **fold into `/nlquery`**
+ keep chat persistence (Mongo or move to Postgres `chat` table — decision in §9).

---

## 7. Frontend rebuild (Felt-like)

Replace the three ad-hoc Leaflet maps with **one MapLibre GL map + a real layer system**.

- **Map core:** MapLibre GL, vector basemap (e.g. a free style), our MVT layers from Martin.
- **Layer panel (the Felt centerpiece):** list of layers with visibility toggle, opacity
  slider, drag-reorder, per-layer styling (color ramp / category colors), and a **legend** per
  layer. Layer groups mirror the data table (Administrative, Roads/Transport, POIs, Real Estate,
  Population, Crime, Environment).
- **NL query bar:** ask → the returned GeoJSON becomes a **new styled "answer" layer** on top,
  with the explanation + SQL in a side panel.
- **Tools:** draw (point/line/polygon), measure distance/area, radius/buffer select, click-to-inspect
  feature. Upload CSV/GeoJSON → your own layer.
- **Saved & shareable maps:** serialize layer state + viewport to a URL / saved record.
- **Cleanups:** kill random-jitter coords, retire dead `App.css`, local Tailwind, env-based API
  base, fix dark mode, consolidate map state into one store (Zustand).

---

## 8. Phased roadmap

Each phase ends with something **demo-able**. Vertical slice first, then broaden.

| Phase | Goal (demo-able outcome) | Key work |
|---|---|---|
| **M0 — Foundations** | `docker compose up` → PostGIS + Martin running; FastAPI connects; one MapLibre map renders a vector basemap. | Compose file, DB schema migrations, Martin config, MapLibre shell. |
| **M1 — Real data, one city (Mumbai)** | Mumbai admin boundaries + roads + POIs + real-estate points visible as toggleable **layers** with legends. | osmnx/Overpass ETL, geocode house-price localities, migrate crime.json, seed `schema_catalog`. |
| **M2 — NL query engine (vertical slice)** | Ask *"hospitals within 1km of Bandra with a park nearby"* → real PostGIS result rendered as an answer layer + explanation + shown SQL. | Multi-agent pipeline §5, execution/review loop, `/nlquery`. |
| **M3 — Felt-grade UI** | Full layer panel (opacity/reorder/style), draw & measure, click-inspect, saved/shareable map. | Layer store, styling controls, tools, share URLs. |
| **M4 — Any city** | Type a new city → ingest on demand → same features work. | Generalize ETL, city resolve/ingest endpoints, progress UI. |
| **M5 — Site-selection + GeoLLM** | *"Best area to open a streetwear store"* → weighted multi-criteria layer with **modeled** footfall proxies, transparent scoring. | Scoring planner, GeoLLM feature scorer, weight UI. |
| **M6 — Polish & defense** | Population/demographics + environment (AQI/flood) layers; upload-your-data; export; write-up mapping papers→features. | Remaining layers, export, docs, eval numbers. |

**Realistic MVP for a strong major-project defense = M0–M3** (one city, real data, working NL
engine, Felt-like UI). M4–M6 are the differentiators if time allows.

---

## 9. Decisions (locked 2026-07-30)
1. **Chat history store** — ✅ **Keep MongoDB.** The existing Mongo chat code stays; Postgres is spatial-only.
2. **Basemap style** — ✅ **MapTiler free tier** via `VITE_MAPTILER_KEY`. Falls back to a free open MapLibre style when no key is set, so the app always runs.
3. **Ingestion trigger** — ✅ **Pre-bake Mumbai** (instant demos) + **on-demand** ingest for any other city (with progress UI).
4. **LLM for SQL-gen** — Stay on Groq llama-3.3-70b for now (abstracted behind a provider interface; revisit at M2 if accuracy needs it).

## 10. Risks
- **OSM data volume** per city can be large → ingest by bbox + selected categories, cache, index.
- **Geocoding rate limits** (Nominatim) → self-host or cache aggressively.
- **LLM SQL correctness** → the execution-review loop + allowlist + read-only role are the mitigations; measure accuracy on a small benchmark (mirrors the papers' eval).
- **Scope** → M0–M3 is the committed core; everything after is explicitly optional.
```
