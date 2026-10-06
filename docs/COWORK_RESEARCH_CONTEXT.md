# GeoQuery Sentinel — Research Report Context (for Cowork)

Purpose: everything needed to draft a research paper/report on this project without opening the
codebase. Facts below were verified against the repo on 2026-10-06. Items marked **[GAP]** are not
yet measured — do not invent numbers for them; leave placeholders or request the experiment.

## 1. One-paragraph summary
GeoQuery Sentinel is a Felt-style layered web map driven by a natural-language → PostGIS spatial-query
engine, grounded in real open data (OpenStreetMap + a 76k-row Mumbai house-price CSV + area-level crime
data). A user asks a spatial question in English; a multi-agent LLM pipeline produces a validated,
read-only PostGIS query, executes it, self-repairs on error/empty results, and returns a GeoJSON answer
layer, a grounded explanation, and the SQL. On top of the engine sit real-estate decision tools: a
click-to-evaluate site card, a business cost/revenue estimator, and a competitor/catchment analysis.
Pre-baked for Mumbai; ETL is designed to generalise to any city.

## 2. Problem and motivation
- **POC baseline (v1) weaknesses**: the LLM invented area names *and coordinates* (hallucination);
  ranking was a fixed hand-weighted formula over ~40 areas with synthetic 1–10 metrics; map markers
  used random coordinate jitter; Leaflet raster maps, no real spatial computation.
- **Thesis**: replace "LLM hallucinates the answer" with "LLM writes a structured spatial query that is
  executed on real data", so every output is verifiable, reproducible and carries provenance (SQL shown).

## 3. Related work to cite (from docs/ARCHITECTURE.md §1)
| Work | Used for |
|---|---|
| Spatial Text-to-SQL multi-agent, arXiv 2510.21045 | 5-stage pipeline; execution-based reviewer stage (paper reports ~+11 pt) |
| ChatGeoAI, ISPRS IJGI 13(10):348 | NL → executable geospatial operations for non-experts |
| GeoLLM, arXiv 2310.06213 (ICLR'24) | LLM + OSM features to model metrics lacking ground truth (planned, M5) |
| NL↔GIS multi-agent frameworks, IJDE 2278895 / IEEE | task decomposition + validation loops |
| Felt.com | product/UX bar (layer system, shareable maps) |

Verify exact bibliographic details before citing; suggested additional literature to search: Text-to-SQL
surveys, Spider/BIRD benchmarks, GeoSQL/Spatial-SQL benchmarks, MCDA weighting (below).

## 4. System architecture
- **Data**: PostgreSQL 16 + PostGIS 3.4 + pgvector (Docker, host port 5433). Schemas: `admin`, `roads`,
  `transport`, `poi`, `realestate`, `demo`, `crime`, `env`, plus `meta.schema_catalog` (34 rows) and
  `core.city`. All geometry EPSG:4326, GiST-indexed, every row tagged `city_id`.
- **Tiles**: Martin serves MVT vector tiles straight from PostGIS.
- **ETL** (`etl/`): osmnx polygon-based ingest (generalises to any city), Nominatim geocoding of
  228 real-estate localities, crime.json migration.
- **Backend**: FastAPI; LLM = Groq `openai/gpt-oss-120b` (changed from llama-3.3-70b; no temperature set)
  behind `app/services/groq_client.py`; MongoDB keeps chat history only.
- **Frontend**: React 19 + MapLibre GL, Zustand store, toggleable styled vector layers with legends,
  click-inspect, NL query bar, Site Evaluation panel.
- **Loaded Mumbai data**: 48 admin boundaries, 16.8k road segments, 2.2k transit stops, 10.8k POIs,
  55.6k real-estate points, 40 crime areas.

## 5. NL → PostGIS engine (`app/services/geo_engine.py`) — the research core
Pipeline, per request `POST /nlquery`:
1. **Interpret** — LLM returns JSON `{is_clear, task_type ∈ filter|proximity|ranking|aggregation|site_selection|other, message, entities}`; biased toward is_clear=true; vague queries get a follow-up question.
2. **Schema-grounded SQL generation** — a compact authoritative `SCHEMA_DOC` is injected (tables, columns,
   enums), with explicit grounding rules (see below).
3. **Validate** — single SELECT/WITH only; semicolon and forbidden-keyword regex (insert/update/delete/drop/…).
4. **Execute** — as the `geo_readonly` DB role, statement timeout, folded into a GeoJSON FeatureCollection,
   capped at 5,000 features.
5. **Self-repair** — on DB error: error text fed back (max 2 repairs; up to 4 total attempts). On valid-but-empty
   result: one "loosen it" retry (ILIKE, wider buffer, resolve names via gazetteer). Best non-empty attempt kept.
6. **Explain** — LLM writes 2–4 sentences from the first 15 returned rows (grounded in actual results).

Output: `{answer GeoJSON, explanation, sql, count, task_type, attempts[]}` — `attempts` logs every SQL try
and its error/row-count, which is ready-made data for an error-taxonomy analysis.

**Key grounding findings (publishable observations)**
- OSM ward names are coded (`K/W Ward`, `H/E Ward`) and do not contain neighbourhood names → LLMs fail on
  "in Bandra". Fix: `crime.area` (~40 named points) doubles as a **neighbourhood gazetteer**; "in <area>" is
  resolved by joining to it with a ~2 km `ST_DWithin` on `::geography`.
- `poi.place` is the only amenity table; `transport.stop.mode` ∈ {bus, metro, rail, tram} and is never an amenity —
  without this rule the model mixes them up.
- "hospital" → `category IN ('hospital','clinic','doctors')` (category-synonym expansion).
- Metric distances require `::geography` casts (EPSG:4326 degrees otherwise).
- Verified manually: hospitals-near-metro, cafes-in-Bandra, cheapest-2BHK, safest-areas.

**Safety guardrails**: read-only DB role, keyword/semicolon validation, statement timeout, feature cap,
`city_id` scoping, provenance (SQL) returned with every answer.
*Note for honesty*: the guardrail is a regex + role privileges, not an AST allow-list or parameterised queries;
the architecture doc's "table/function allow-list" is not implemented in code. Describe it accurately.

## 6. Decision-support features built on the data (M3)
- **Site evaluation** (`site_evaluator.py`, `POST /site-eval`): for a clicked point — nearby comps (median ₹/sqft,
  price band, per-BHK), vs-city-median chip, nearest transit per mode, amenity counts by bucket
  (healthcare/education/food/banking/shopping), nearest crime-area safety score.
- **Business cost estimator** (`business_estimator.py`, `POST /business-estimate`): rent = local median ₹/sqft
  (listings within 2 km) × 0.5 %/month × 1.15 commercial premium; LLM-generated line items (interior, equipment,
  stock, staff, utilities, licences) split one-time vs monthly + working-capital buffer; heuristic fallback if the
  LLM is down; revenue scenarios from per-business-type benchmarks (`REV_BENCH`: ticket size, footfall per 100,
  COGS %), outputs payback months, break-even revenue and break-even daily customers. Printable plan document.
  Spot checks: Bandra café ≈ ₹62 L to start; Lower Parel premium restaurant ≈ ₹1.3 Cr.
- **Competitor/catchment analysis** (`competitor_analysis.py`, `POST /competitor-analysis`): same-category POIs in
  radius, density/km² → low/moderate/high/saturated, demand index (0–100) from business-type-specific weights over
  catchment buckets + transit, 5×5 grid gap scan ranking spots by demand ÷ competition. Thresholds/weights are
  heuristics (stated in the response); counts and locations are measured.
- **Comparison panel** (`ComparePanel.jsx`) for side-by-side sites. Phase 2 TODO: neighbourhood ₹/sqft choropleth.

## 7. Existing quantitative evidence — Weight-sensitivity study (`eval/weight_study.py`)
Full tables/figures: `eval/results/weight_study/summary.md` (+10 PNGs, CSVs). runs=1000, seed=42, 40 areas, top-k=5.
Caveat: it analyses the **legacy POC scoring** over `crime.json` (synthetic 1–10 site metrics), not the PostGIS engine.
Frame it as a sensitivity/robustness analysis of the multi-criteria ranking and women-safety score.

**A. Site ranking** (5 criteria: footfall, youth, access, rent, competition; baseline weights .30/.25/.20/.15/.10)
- Weighting schemes compared: hand-picked baseline, Equal, ROC, AHP (CR = 0.011, acceptable), Entropy, CRITIC,
  3 scenarios (Budget/Student/Premium), TOPSIS.
- Agreement with baseline (Kendall τ): AHP 0.923, Student 0.873, Premium 0.832, ROC 0.813, Entropy 0.578,
  Equal 0.413, TOPSIS 0.361, Budget −0.113, CRITIC −0.008 (n.s.). Top-5 overlap: AHP/ROC/Premium = 5/5; CRITIC = 0.
- One-at-a-time ±30 % on a weight: worst-case τ ≥ 0.903 (most sensitive: access 0.903, footfall 0.909).
- Monte Carlo (1000 Dirichlet(1) weight sets): median τ = 0.331 (5th pct −0.489, 95th 0.842) → **ranking is
  highly weight-dependent**; Andheri West is top-5 in only 44.5 % of draws (baseline rank 1, median rank 11).
- Takeaway: hand-picked weights are defensible only near AHP/ROC; objective schemes (CRITIC/Entropy) disagree
  strongly → motivates transparent, user-adjustable weights and reporting stability.

**B. Women-safety score** (violent, harassment, kidnapping, cyber, NDPS, brothel)
- Kidnapping component is always 0 (no data) → excluded from OAT/MC analyses.
- Very robust: all schemes top-5 overlap 5/5, τ 0.92–0.997; OAT worst-case τ ≥ 0.985; MC median τ 0.949
  (5th pct 0.844, 95th 0.985).
- External validity: Spearman vs total recorded cases −0.895…−0.939 (p < 1e-14); vs independent dataset safety
  score +0.902…+0.930.

## 8. Planned/required experiments (the paper's results section) — **[GAP: none run yet]**
No NL→SQL benchmark or eval harness exists in the repo (only `eval/weight_study.py`). The plan (from memory notes):
1. **Pipeline ablation**: zero-shot → +schema doc → +grounding rules → +error repair → full pipeline.
2. **LLM backbone comparison**: e.g. llama-3.3-70b vs gpt-oss-120b (+ others) on the same benchmark.
3. **POC-vs-rebuild hallucination study**: fraction of returned areas/coordinates that do not exist in real data.
4. **Per-category accuracy + error taxonomy** (use the `attempts[]` log): wrong table, wrong column, name
   resolution failure, missing geography cast, over-strict filter (empty result), syntax error.
5. **Qualitative related-systems table** (vs Felt, ChatGeoAI, 2510.21045 system, Google/Esri tools).
Suggested metrics: execution accuracy (executes without error), result-set correctness vs gold SQL (row-set F1 /
Jaccard on returned feature ids), empty-result rate, repair-success rate, avg attempts, latency, tokens/cost.
Suggested benchmark: 50–100 hand-written Mumbai questions across proximity, filter, ranking, aggregation,
named-area, multi-hop; gold SQL authored and verified by the team.

## 9. Limitations to state honestly
- Single city (Mumbai) in practice; "any city" is an ETL design property, not yet demonstrated (M4).
- Demographics and environment layers (`demo.cell`, `env.measurement`) are empty; population/AQI/flood questions unsupported.
- Crime data is area-level aggregate points, not incident-level; real-estate points are geocoded to locality centroids
  (228 regions), so within-locality precision is limited.
- Business cost/revenue figures rely on benchmark tables + LLM line items; heuristic, not validated against real P&Ls.
- Competitor demand weights and saturation thresholds are expert-set heuristics.
- Guardrails: regex/role based, no AST allow-list. LLM temperature unset (non-deterministic outputs); no
  schema-embedding retrieval yet — the full SCHEMA_DOC is injected in the prompt (pgvector catalogue exists but
  isn't used for retrieval in the engine).
- Weight study covers the legacy scoring and synthetic site metrics.

## 10. Suggested paper structure
Abstract · Introduction (problem, thesis, contributions) · Related Work · System Design (data, ETL, engine,
guardrails) · Grounding Techniques (gazetteer, enum rules, geography casts, repair loop) · Decision-support
modules (site eval, cost/revenue, competition) · Evaluation (§7 existing + §8 to-run) · Discussion & Limitations ·
Conclusion/Future work (M4 any-city, M5 GeoLLM modelled metrics, retrieval-based grounding).

Candidate contributions: (1) end-to-end NL→PostGIS system on real open data with provenance; (2) grounding
insights for LLMs on coded admin boundaries (gazetteer trick); (3) execution-feedback repair for spatial SQL
incl. empty-result loosening; (4) sensitivity analysis showing MCDA site rankings are weight-fragile while
safety scores are robust; (5) integrated real-estate decision tooling.

## 11. File map (where to look)
| Topic | Path |
|---|---|
| Plan, tech choices, roadmap | `docs/ARCHITECTURE.md`, `docs/RUNBOOK.md` |
| NL→SQL engine | `app/services/geo_engine.py`, `app/routes/nlquery.py` |
| LLM client | `app/services/groq_client.py` |
| Site / cost / competition | `app/services/{site_evaluator,business_estimator,competitor_analysis}.py` |
| DB schema | `db/init/02_schema.sql`; ETL in `etl/` |
| Sensitivity study | `eval/weight_study.py`, `eval/results/weight_study/` |
| Existing slide decks | `docs/other/*.pptx` (Somaiya PBL presentation) |
| Test prompts | `prompts.md` |
