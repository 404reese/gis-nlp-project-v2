#import "@preview/charged-ieee:0.1.4": ieee

// Marker for numbers or facts that still have to be measured or confirmed.
// Search the file for "TODO" before submitting.
#let todo(body) = text(fill: red, weight: "bold")[\[TODO: #body\]]

#show: ieee.with(
  title: [GeoQuery Sentinel: A Natural-Language Geospatial\ Query and Site-Evaluation System on PostGIS],
  abstract: [
    Geospatial analysis supports urban planning, retail strategy and infrastructure decisions, yet traditional GIS platforms demand expertise in spatial query languages and specialised software. Large language models (LLMs) can lower this barrier, but systems that let the model answer directly tend to hallucinate place names and coordinates, which makes their output unverifiable. This paper presents GeoQuery Sentinel, a Felt-style layered web map driven by a natural-language to PostGIS query engine grounded in open data. A user asks a spatial question in English, for example "hospitals within 1 km of a metro station". An LLM writes a PostGIS query against a documented schema, the query is executed on real data, and the system returns a GeoJSON answer layer, a grounded explanation and the SQL itself, so every answer carries provenance. On top of the engine we build real-estate decision tools: a click-to-evaluate site report, a competition and catchment analysis, a cost-to-open and break-even estimator, and a side-by-side comparison of up to three candidate locations. The system runs on PostgreSQL 16 with PostGIS 3.4, serves vector tiles with Martin, and renders them with MapLibre GL. It is loaded with Mumbai data from OpenStreetMap, a 76,000-row house-price dataset and area-level crime data, and its ETL is designed to generalise to other cities. We describe the architecture, the decision models and their current limitations, and outline the benchmark needed to measure query accuracy.
  ],
  authors: (
    (
      name: "Riddhesh Chaudhary",
      department: [Department of Artificial Intelligence & Data Science],
      organization: [K.J. Somaiya Institute of Technology],
      location: [Mumbai, India],
      email: "riddhesh.c@somaiya.edu"
    ),
    (
      name: "Arpit Balmiki",
      department: [Department of Artificial Intelligence & Data Science],
      organization: [K.J. Somaiya Institute of Technology],
      location: [Mumbai, India],
      email: "arpit.b@somaiy.edu"
    ),
    (
      name: "Chirayu Vyas",
      department: [Department of Artificial Intelligence & Data Science],
      organization: [K.J. Somaiya Institute of Technology],
      location: [Mumbai, India],
      email: "chirayu.vyas@somaiya.edu"
    ),
  ),
  index-terms: ("Generative AI", "GIS", "Natural Language Processing", "Text-to-SQL", "Spatial SQL", "PostGIS", "Site Selection"),
)

= Introduction
Geospatial data is central to urban planning, transportation, environmental monitoring and retail analytics. Geographic Information Systems (GIS) have traditionally been the main tools for such analysis, but they require users to understand spatial data handling, query languages such as SQL, and specialised software. This creates a barrier for the many people who have location questions but no GIS training.

Web platforms such as Felt have made map creation, collaboration and visualization much easier @felt. Even so, users must still translate a real-world question into manual operations on layers and filters. At the same time, LLMs have made natural-language interfaces to structured data practical, and recent work applies them to spatial data @chatgeoai @spatialt2s.

A naive way to build such an interface is to let the LLM answer the question itself. Our first proof of concept (POC) did this and exposed three weaknesses. The model invented area names and coordinates. Ranking used a fixed hand-weighted formula over about 40 areas with synthetic 1 to 10 metrics. Map markers were placed with random coordinate jitter, and the maps were Leaflet raster maps with no real spatial computation. None of the outputs could be checked.

The central idea of this work is to replace "the LLM hallucinates the answer" with "the LLM writes a structured spatial query that is executed on real data". Every output is then verifiable and reproducible, and the generated SQL is shown to the user as provenance.

GeoQuery Sentinel implements this idea as a full-screen layered map with a natural-language query bar. Beyond exploratory queries, it supports decision-oriented work for prospective business owners: evaluating a clicked location, analysing local competition and catchment demand, estimating the cost to open a store, and comparing candidate sites. The main contributions are:

+ A natural-language to PostGIS query engine that grounds the LLM in a documented schema and returns a GeoJSON layer, an explanation and the executed SQL.
+ A real-data foundation: an ETL pipeline that loads OpenStreetMap, real-estate listings and crime data into a single spatial database, designed to work for any city.
+ A set of decision tools (site evaluation, competition analysis, cost-to-open, location comparison) built on the same data.
+ An honest account of what is and is not yet validated, together with the evaluation plan for the missing pieces.

= Literature Survey
Traditional GIS platforms such as ArcGIS and QGIS provide buffering, proximity analysis and spatial querying, but assume knowledge of spatial concepts, data formats and query languages. Cloud platforms such as Felt and Mapbox improve collaboration and visualization @felt, yet users still drive them through layers, filters and map controls.

Natural-language interfaces to databases map a question to an executable query. Benchmarks such as Spider @spider and BIRD @bird have driven progress on general text-to-SQL, with LLM-based systems now dominating. Spatial questions add difficulty: the model must pick the right geometry types, apply spatial predicates and distance functions correctly, and respect coordinate reference systems. Early geospatial interfaces used rule-based mapping from keywords such as "near" and "within" to spatial operations. These are effective for simple queries but brittle for ambiguous or compositional ones.

More recent work uses LLMs for geospatial tasks. A multi-agent spatial text-to-SQL pipeline reports that adding an execution-based review stage improves accuracy by roughly 11 points @spatialt2s. ChatGeoAI converts natural language into executable geospatial operations for non-expert users @chatgeoai. GeoLLM shows that LLMs combined with OpenStreetMap features can model quantities for which ground truth is scarce @geollm. We take the first two as the design reference for our query engine. The 11-point figure is a result from that work, not from ours. We treat GeoLLM as relevant to estimating metrics, such as rent, where no direct data exists.

Spatial decision support systems extend GIS with multi-criteria decision analysis (MCDA) for tasks such as site selection @malczewski. They rank candidates by combining normalised criteria with weights, but typically require expert configuration and expert interpretation of the result.

OpenStreetMap (OSM) provides free, globally available data on roads, amenities and land use @osm, and tools such as OSMnx make it easy to acquire polygon-bounded extracts for any city @osmnx. PostGIS adds spatial types, GiST indexing and spatial functions to PostgreSQL, which makes it a suitable execution target for generated queries.

Existing systems tend to cover either visualization, query processing or decision support. We combine all three on one open-data stack, with the emphasis on verifiable query results.

= Proposed System
GeoQuery Sentinel lets users interact with geospatial data in plain English and then act on the results with decision tools. The primary workspace (`/studio`) is a full-screen map with a left panel of toggleable layers, a natural-language query bar, and panels for evaluating, comparing and costing locations.

== Problem Statement and Objectives
=== Problem Statement

Geospatial analysis is essential for business planning and urban development, but existing GIS tools are complex and demand knowledge of spatial data structures and query languages. Most also focus on visualization, leaving users to interpret patterns by hand. A person deciding where to open a cafe must weigh nearby prices, transit access, safety, competition and start-up cost, and no single easy tool combines these.

LLM-based interfaces reduce the technical barrier, but when the model supplies the answer directly, place names and coordinates can be invented and nothing can be verified. There is a need for a system that accepts natural language, computes answers on real spatial data, shows how each answer was obtained, and supports practical location decisions.

=== Objectives

The primary objective is to build a natural-language geospatial query and decision-support system whose answers are computed from real data. The specific objectives are:

+ *To provide a natural-language interface* that lets users ask spatial questions in plain English without SQL or GIS knowledge.
+ *To translate questions into PostGIS queries* using an LLM grounded in a documented schema, and to return the result as a map layer, an explanation and the SQL.
+ *To build a spatial data foundation* on PostgreSQL and PostGIS from OpenStreetMap, real-estate listings and crime data, with an ETL pipeline that generalises to other cities.
+ *To serve and render layers efficiently* using vector tiles, with a toggleable layer panel and click-to-inspect interaction.
+ *To support location decisions* through a site evaluation report, competition and catchment analysis, a cost-to-open and break-even estimator, and a side-by-side comparison of candidate locations.
+ *To keep results explainable* by generating plain-English explanations and exposing the executed SQL.
+ *To remain cost-effective* by using open-source tools and open data.

== Methodology

The system is a modular pipeline. A question enters through the query bar, the backend turns it into a spatial query, the database executes it, and the frontend draws the answer. Decision tools reuse the same database through dedicated endpoints.

#figure(
  {
    let stage(t) = block(width: 100%, stroke: 0.6pt, inset: 4pt, radius: 2pt, align(center, text(size: 7.5pt, t)))
    let arrow = align(center, text(size: 8pt, sym.arrow.b))
    stack(
      dir: ttb,
      spacing: 2pt,
      stage[User question (natural language)],
      arrow,
      stage[Intent check (clear spatial query?)],
      arrow,
      stage[LLM generates PostGIS SQL from the schema description],
      arrow,
      stage[Validate, then execute as read-only role],
      arrow,
      stage[Repair on DB error or empty result (bounded)],
      arrow,
      stage[GeoJSON layer + grounded explanation + SQL],
      arrow,
      stage[MapLibre map, answer panel],
    )
  },
  caption: [Natural-language query pipeline of GeoQuery Sentinel.],
) <fig-pipeline>

=== Explanation of Methodology

+ *User input.* The user types a spatial question, either exploratory ("hospitals within 1 km of a metro station") or decision-oriented.
+ *Intent check.* A first LLM call decides whether the question is a clear spatial query and labels its task type (filter, proximity, ranking, aggregation, site selection or other). If the target is genuinely unknowable, for example "best place?", the system returns a short follow-up question instead of running a query.
+ *Schema grounding.* The SQL-generating call receives a compact, authoritative description of the queryable schema embedded in the prompt. It lists the tables and columns of the `admin`, `roads`, `transport`, `poi`, `realestate`, `demo`, `crime` and `env` schemas with their geometry types, the allowed values of key categorical columns, and explicit rules: filter every table by `city_id`, never reference a table or column that is not listed, and emit one read-only `SELECT` with a geometry column named `geom`. Grounding on this description is what prevents the model from inventing places: it can only reference data that exists. The same information is also stored in the database as a 34-row `meta.schema_catalog` table, but the query engine does not read that table at query time.
+ *Query generation.* The LLM (Groq `openai/gpt-oss-120b`, behind a single client module) writes a PostGIS query using functions such as `ST_DWithin` and `ST_Contains`. All geometry is in EPSG:4326 and indexed with GiST, and every row carries a `city_id`. The returned text is validated before execution: it must be a single `SELECT` or `WITH` statement with no chained statements and no data-modifying or DDL keywords.
+ *Execution.* The query runs on PostgreSQL 16 with PostGIS 3.4 as a dedicated `geo_readonly` role, with a 15 second statement timeout and a cap of 5,000 returned features.
+ *Repair.* If the query fails validation or raises a database error, the error text is fed back to the model for a corrected query, with at most two such repairs. If a valid query returns zero rows, the model is asked once to loosen it. The best successful attempt is kept, preferring a non-empty one, and every attempt is returned to the client.
+ *Result generation.* Rows are converted to a GeoJSON answer layer, and the LLM writes a short explanation grounded in a sample of the returned rows. The generated SQL is returned alongside, so users can inspect how the answer was obtained.
+ *Visualization.* The answer layer is drawn on the map next to the base layers. Base layers are served as Mapbox Vector Tiles by Martin directly from PostGIS.

Chat history is stored in MongoDB. It is not used for spatial data.

== Analysis, Framework and Algorithm
=== System Framework Overview
The system has three layers: a presentation layer (React and MapLibre GL), an application layer (FastAPI endpoints and the LLM client), and a data layer (PostGIS, Martin and MongoDB). This separation keeps the model, the query execution and the rendering independently replaceable.

=== Algorithm for Query Processing
```py
def answer(question, city_id):
    intent = llm.interpret(question)           # clear spatial query?
    if not intent.is_clear:
        return intent.follow_up                # ask the user, no query run
    best, error, empty = None, None, False
    for _ in range(MAX_REPAIRS + 2):
        sql = llm.generate_sql(question, SCHEMA_DOC, error, empty)
        try:
            sql = validate_select(sql)         # single read-only SELECT
            layer = execute_readonly(sql)      # geo_readonly, 15 s timeout
        except Exception as e:
            error, empty = str(e), False       # feed the error back
            continue
        if best is None or layer.count > best.count:
            best = (sql, layer)
        if layer.count > 0: break
        if empty: break                        # one loosening attempt only
        error, empty = None, True
    text = llm.explain(question, best.rows)    # grounded in returned rows
    return best.layer, text, best.sql          # SQL returned as provenance
```

The loop makes at most four generation attempts: the first, up to two repairs after errors, and one loosening after an empty result. This follows the execution-based review idea of @spatialt2s in a simplified form. The effect of the repair stage on accuracy has not yet been measured.

=== Decision Support Models
The decision tools are built on the same database and exposed as separate endpoints (`/site-eval`, `/competitor-analysis`, `/business-estimate`).

*Site evaluation.* For a clicked point and a radius between 0.5 and 3 km, the report gives the median price per sqft of nearby listings, a typical price band, a comparison with the city median, a breakdown by size band, the nearest metro, rail and bus stops, amenity counts (healthcare, education, food, banking, shopping), and a safety score with a risk level.

*Competition and catchment analysis.* The report gives the competitor count, density, nearest competitor and a saturation label, together with a 0 to 100 catchment demand index. It also suggests lower-competition spots, shown as green markers, while competitors are drawn as red dots. Competitors are points in `poi.place` whose category matches the business type (for a cafe, the category `cafe`) inside the chosen radius, and density is the count divided by the area of the circle. The saturation label uses fixed bands of competitors per km#super[2]: below 5 is low, 5 to 15 moderate, 15 to 30 high and above 30 saturated. These bands, like the demand weights below, are heuristics set by judgement and have not been calibrated against business outcomes. The demand index counts the points of interest in five groups (healthcare, education, food, banking and shopping, mapped from OSM categories) and the transit stops inside the radius. Each count is capped at a saturation value (40, 25, 40, 15, 30 and 12 respectively), so that very dense areas do not dominate, and the capped counts are combined with business-specific weights, for example a pharmacy weights healthcare heavily and a cafe weights education, shopping and transit. The result is scaled to 0 to 100. To suggest gaps, a 5 by 5 grid of candidate spots is laid over the radius. Each spot receives an opportunity score equal to its demand index divided by one plus its number of competitors within 500 m. Up to three spots with a demand index of at least 15 and an opportunity score at least 15% higher than the evaluated spot are suggested.

*Cost-to-open and break-even.* The estimator takes a store area in sqft and returns one-time setup costs, monthly running costs, staff cost and working capital. Rent is estimated from nearby sale prices, because rental data is not yet available. The monthly rent per sqft is the median sale price per sqft of listings within 2.5 km, multiplied by 0.5% (a monthly rent-to-value ratio) and by a commercial premium of 1.15. If no listing is found nearby, a city default of 120 rupees per sqft per month is used. The security deposit is six months of rent and working capital is three months of running costs. Other line items are produced by the LLM, with a heuristic fallback when the LLM is unavailable. A revenue and break-even model estimates customers per day as the store area (per 100 sqft) times a benchmark rate for the business type, a footfall multiplier between 0.6 and 1.5 derived from amenities within 1 km and metro or rail access within 800 m, and a competition factor of $1 / (1 + 0.04 n)$, floored at 0.6, where $n$ is the number of competitors within 1 km. Revenue is customers times an average ticket (scaled by 0.8, 1.0 or 1.3 for economy, standard or premium tier) times 30 days. Cost of goods is a fixed share of revenue and replaces the fixed restock line, and profit is revenue minus cost of goods minus the remaining monthly costs. The conservative, base and optimistic scenarios scale the customer count by 0.7, 1.0 and 1.3. Payback is the one-time setup cost divided by monthly profit, and break-even revenue is the remaining monthly cost divided by one minus the cost-of-goods share. The per-type benchmarks (customers per sqft, average ticket and cost-of-goods share) are modelling assumptions set by the authors and not measured values. The plan can be downloaded or printed.

*Location comparison.* Up to three pinned spots (A, B, C) are shown side by side across price, access, safety, competitors, rent, start-up cost, revenue, profit and payback. The best value in each row is marked.

*Area-level weighted ranking (legacy dashboard).* The original dashboard ranks areas with a standard weighted-sum MCDA model @malczewski. For area $i$ with criteria $m_(i k)$ (footfall, youth, access, rent and competition, each scored from 0 to 10),

$ S_i = sum_(k=1)^K w_k thin m'_(i k), quad sum_(k=1)^K w_k = 1, $

where $m'_(i k) = m_(i k)$ for benefit criteria (footfall, youth, access) and $m'_(i k) = 10 - m_(i k)$ for criteria for which lower is better (rent and competition). The hand-picked weights are 0.30, 0.25, 0.20, 0.15 and 0.10 in that order, and the five highest-scoring areas are returned. In the POC the metrics were synthetic and the weights fixed by hand.

To test how much the ranking depends on these weights we ran a sensitivity study on the 40 scored areas (script in the `eval/` folder). We compared the hand-picked weights with equal weights, rank-order centroid (ROC) weights, AHP weights (consistency ratio 0.011), entropy weights, CRITIC weights and three scenario weight sets (budget, student and premium), and we compared the weighted sum with TOPSIS under the baseline weights. Agreement with the baseline ranking was measured by Kendall's $tau$ and by the overlap of the top five areas. We also perturbed each weight by up to 30% one at a time, and drew 1,000 random weight vectors from a uniform Dirichlet distribution (seed 42) to see how often each area stays in the top five.

The ranking is stable under small changes to a single weight: the worst-case $tau$ for a 30% change in any one weight is 0.90 or higher (lowest for the access weight). It is not stable under a change of weighting scheme. AHP, ROC and the premium scenario keep the same top five as the baseline (Kendall $tau$ of 0.92, 0.81 and 0.83), while equal weights, entropy weights, the student scenario, the budget scenario, TOPSIS and CRITIC share only 2, 2, 2, 1, 1 and 0 of the baseline's top five areas ($tau$ of 0.41, 0.58, 0.87, -0.11, 0.36 and -0.01). Across random weight vectors the median $tau$ against the baseline is 0.33 (5th to 95th percentile: -0.49 to 0.84), and no area stays in the top five in more than 45% of draws (Andheri West is highest at 44.5%). The weights therefore encode a preference, not a neutral measurement, which is one reason the Sentinel workspace uses measured spatial queries in place of this fixed ranking. These results describe the 40-area scored dataset and should not be read as evidence about real-world site quality.

== Details of Hardware and Software

=== Hardware Requirements
The system runs on a standard personal computer or laptop.

- Processor: Intel i5 or equivalent (or higher recommended)
- RAM: minimum 8 GB (16 GB recommended for large datasets)
- Storage: at least 20 to 50 GB free (OpenStreetMap data and database)
- Network: internet connection for the LLM API and geocoding

=== Software Requirements

The stack is primarily open source.

#table(
  columns: (auto, 3cm, 1fr),
  inset: 3pt,
  align: horizon,
  fill: (x, y) => if y == 0 { silver } else { none },
  stroke: 0.5pt + gray,
  [*Sr. No.*], [*Software/Tool*], [*Description*],
  [1], [PostgreSQL 16 + PostGIS 3.4], [Spatial database with GiST indexing; pgvector extension also installed],
  [2], [Martin], [Serves Mapbox Vector Tiles directly from PostGIS],
  [3], [FastAPI + Uvicorn], [REST backend for the query engine and decision tools],
  [4], [Groq API (`openai/gpt-oss-120b`)], [LLM for SQL generation, explanations and cost line items],
  [5], [React 19 + Zustand], [Frontend and client state],
  [6], [MapLibre GL], [Vector-tile map rendering in the main workspace],
  [7], [Leaflet], [Map in the legacy dashboard only],
  [8], [OSMnx], [Polygon-based OpenStreetMap ingest for any city],
  [9], [Nominatim], [Geocoding of 228 real-estate localities],
  [10], [MongoDB], [Chat history only],
  [11], [Docker], [Runs the database and supporting services],
)

== Design Details

=== System Architecture Overview

#figure(
  table(
    columns: (auto, 1fr),
    inset: 3pt,
    stroke: 0.5pt + gray,
    align: (left + horizon, left + horizon),
    fill: (x, y) => if x == 0 { silver } else { none },
    [*Presentation*], [React 19, MapLibre GL, Zustand; layer panel, query bar, evaluation panel],
    [*Application*], [FastAPI endpoints, LLM client (`groq_client.py`), MongoDB chat history],
    [*Tiles*], [Martin serving MVT from PostGIS],
    [*Data*], [PostgreSQL 16 + PostGIS 3.4 + pgvector; schemas `admin`, `roads`, `transport`, `poi`, `realestate`, `demo`, `crime`, `env`; `meta.schema_catalog`; `core.city`],
    [*ETL*], [OSMnx ingest, Nominatim geocoding, crime data migration],
  ),
  caption: [System component stack.],
) <fig-stack>

=== Module-wise Design

==== Frontend (Studio)
The map is full-screen with OSM base tiles. The left panel toggles vector layers served by Martin, each with an opacity slider: administrative boundaries, road network, transit stops, businesses and POIs, real-estate listings, and a crime and safety score. Users can click any feature to inspect it, type a question into the query bar, or click a point to open the evaluation panel with its Competition and Cost-to-open tabs.

==== Backend API
FastAPI exposes `/nlquery` for natural-language queries, `/site-eval`, `/competitor-analysis` and `/business-estimate` for the decision tools, and `/health`. The original dashboard additionally uses `/analyze`, `/generate`, `/explain`, `/query`, `/location-insight`, `/properties` and `/locations`.

==== Spatial Database
The database holds all layers in EPSG:4326 with GiST indexes, and every row is tagged with a `city_id` so several cities can coexist. The schema catalog documents the tables, and the same description is embedded in the model prompt.

==== ETL
The ETL pipeline (`etl/`) ingests roads, transit, POIs and boundaries from OSM with polygon-based extraction, geocodes real-estate localities with Nominatim, and loads crime data. Because extraction is driven by a city polygon, the same pipeline can load other cities. The deployed instance is pre-loaded for Mumbai.

==== Legacy Dashboard
The `/dashboard` page is the original assistant view: a chat assistant that asks clarifying questions and ranks areas, a Leaflet map with a heatmap by factor, a Top Locations panel with explanations, and a location detail view. Where an area has no scored metrics, the detail view borrows them from the nearest scored area. We keep it as the baseline against which the Sentinel workspace is compared.

=== Design Considerations
- Verifiability: the SQL is always shown, and answers come from executed queries.
- Performance: vector tiles and spatial indexes keep map interaction fast.
- Generality: the `city_id` tag and polygon-based ETL support other cities.
- Cost efficiency: the stack uses open-source tools and open data.

== Advantages And Limitation

=== Advantages
+ *Verifiable answers.* Results come from executed queries on real data, and the SQL is shown, which addresses the hallucination problem of direct LLM answers.
+ *Natural-language interface.* Users need no SQL or GIS knowledge.
+ *Decision support.* Site evaluation, competition analysis, cost-to-open and comparison turn a map into a practical planning tool.
+ *Open and low cost.* The stack uses open-source software and open data.
+ *Generalisable.* Polygon-based ETL and `city_id` tagging allow other cities to be added.

=== Limitations
+ *No labelled benchmark.* We have not measured NL to SQL accuracy, so no accuracy claim is made.
+ *Repair stage not evaluated.* The engine retries after a database error or an empty result, but the retries are bounded and we have not measured how much they improve accuracy.
+ *Basic SQL safeguards.* Generated SQL runs under a read-only role with a statement timeout and a row cap, and is checked to be a single `SELECT`. The check is keyword-based and not a full SQL parser, and there is no table allow-list beyond the role's grants.
+ *No real rental data.* Rent is estimated from sale prices, so cost-to-open figures are approximate.
+ *Heuristic decision models.* The saturation bands, demand weights and per-type revenue benchmarks are set by judgement and have not been calibrated against real outcomes.
+ *Coarse listing locations.* Real-estate listings are geocoded at the locality level (228 localities), not per property.
+ *Radius-based catchments.* Catchments are circles, not travel-time isochrones.
+ *Data coverage.* Only Mumbai is loaded, and OSM completeness varies. Crime data is area-level.
+ *Model variability.* The LLM is called without a fixed temperature, so the same question can yield different SQL.
+ *No saved sites or mobile layout.* Pinned locations are not persisted, and the interface is designed for desktop.

= Results And Discussion

== Implemented System

The system is implemented end to end. Table @tab-data lists the Mumbai data currently loaded.

#figure(
  table(
    columns: (1fr, auto),
    inset: 3pt,
    stroke: 0.5pt + gray,
    fill: (x, y) => if y == 0 { silver } else { none },
    [*Dataset*], [*Size*],
    [Administrative boundaries], [48],
    [Road segments], [16.8k],
    [Transit stops], [2.2k],
    [Businesses and POIs], [10.8k],
    [Real-estate listings (CSV)], [76,000 rows],
    [Geocoded real-estate localities], [228],
    [Schema catalog entries], [34],
  ),
  caption: [Mumbai data loaded in the current instance.],
) <tab-data>

Compared with the POC, the Sentinel workspace replaces invented coordinates with coordinates from the database, replaces random marker jitter with real geometries, replaces raster Leaflet maps with vector tiles, and replaces fixed synthetic metrics with metrics computed from nearby listings, transit and amenities.

== Qualitative Demonstration

A query such as "hospitals within 1 km of a metro station" is turned into a spatial SQL query, executed, and drawn as an answer layer, with the explanation and the SQL available in the panel. Clicking a location opens a site report with price, access, amenity and safety information, and the Competition and Cost-to-open tabs extend it to a business decision. #todo[add screenshots of the map, an NL query result, the site report and the comparison table]

== Comparative Analysis

We compare the system along two axes: the query engine against its own ablations and against the direct-LLM approach of the POC, and the weighting schemes of the legacy area ranking.

=== Query engine versus ablations and the direct-LLM baseline

The benchmark in `eval/nl2sql/` contains 39 spatial questions in six categories (filters, proximity, named areas, rankings, listings and compositional queries), each with a hand-written gold SQL query. The expected answer is the executed result of the gold query, and a predicted layer is scored by comparing geometry sets (exact match and F1), so column names do not matter. Four configurations are compared: the full engine, the engine without the repair stage, the engine whose schema description lists only table names, and the direct-LLM baseline in which the model names places and coordinates without a database. The baseline returns no SQL, so it is scored on grounding: the share of returned names that exist in the database and the share of returned points that lie near a real feature.

#todo[run the benchmark and add the results: the table `paper_table.typ` and the charts `bench_accuracy.png`, `bench_by_category.png`, `bench_baseline.png` and `bench_latency.png` written by `eval/nl2sql/run_benchmark.py`, then describe the differences between configurations, with counts and the spread over repeated runs]

=== Weighting schemes of the legacy ranking

The comparison of weighting schemes is described with the decision support models above. @fig-weight-tau shows how far each scheme's ranking is from the hand-picked one, and @fig-weight-oat shows how little the ranking changes when a single weight is changed by up to 30%.

#figure(
  image("figures/weight_tau_bar.png", width: 100%),
  caption: [Rank agreement (Kendall's $tau$) of each weighting scheme with the hand-picked weights, and the overlap of the top-five areas.],
) <fig-weight-tau>

#figure(
  image("figures/weight_oat_sensitivity.png", width: 100%),
  caption: [One-at-a-time sensitivity: Kendall's $tau$ against the hand-picked ranking when one criterion's weight is changed by up to 30%, the others being renormalised.],
) <fig-weight-oat>

== Evaluation Status

The following measurements have not been made and are required before quantitative claims can be added. We deliberately leave them as open items.

#table(
  columns: (1fr, 1fr),
  inset: 3pt,
  stroke: 0.5pt + gray,
  fill: (x, y) => if y == 0 { silver } else { none },
  [*Measurement*], [*Status*],
  [NL to SQL execution accuracy on a labelled benchmark of spatial questions], [Not built. #todo[build benchmark and report accuracy]],
  [Effect of the execution-based repair stage], [Repair stage implemented, effect not measured. #todo[compare accuracy with and without repair on the benchmark]],
  [Latency of `/nlquery` and the decision endpoints], [#todo[measure median and 95th percentile]],
  [Weight sensitivity of area ranking], [Done on the 40-area dataset, see the decision support section],
  [Accuracy of rent estimate against real rents], [No rental data yet],
)

== Discussion

Grounding the model in a documented schema and returning the executed SQL changes the nature of the interface: answers can be checked, reproduced and corrected. The decision tools show that the same data supports practical questions, such as comparing three candidate shop locations on price, access, safety and competition.

The main weakness of the current work is evaluation. Without a labelled benchmark we cannot say how often the generated SQL is correct or how much the repair stage helps. The safeguards, a read-only role, a statement timeout, a row cap and a single-statement check, limit the damage a malformed query can do, but they have not been tested against adversarial input. Cost and revenue estimates inherit the approximations in the rent model, the per-type benchmarks and the LLM-produced line items, and should be treated as planning aids. The weight study shows that the legacy area ranking is sensitive to the choice of weighting scheme.

= Conclusion And Future Scope

== Conclusion

GeoQuery Sentinel shows that a natural-language interface to geospatial data can be built so that answers are computed on real data and are inspectable. By pairing a schema-grounded LLM with PostGIS, vector tiles and open data, it avoids the invented places and coordinates of direct LLM answers, and it extends the query engine with site evaluation, competition analysis, cost-to-open modelling and location comparison for practical decisions. The system is functional for Mumbai, and its ETL is designed to generalise. Quantitative evaluation of query accuracy remains to be done.

== Future Scope
+ *Query reliability:* build a labelled NL to SQL benchmark in the style of Spider and BIRD @spider @bird, and use it to measure and tune the existing repair stage @spatialt2s.
+ *Safety:* replace the keyword check with parser-based validation and a table allow-list.
+ *Data:* integrate real rental data, and extend the metrics modelling with LLM and OSM features where ground truth is scarce @geollm.
+ *Analysis:* replace radius catchments with isochrones, and calibrate the saturation bands and revenue benchmarks against real outcomes.
+ *Usability:* saved sites and a mobile layout.
+ *Coverage:* load additional cities using the existing ETL.

#bibliography("refs.bib", full: false)
