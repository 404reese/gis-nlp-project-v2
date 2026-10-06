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
      stage[Schema context from `meta.schema_catalog`],
      arrow,
      stage[LLM generates PostGIS SQL],
      arrow,
      stage[Execute on PostgreSQL + PostGIS],
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
+ *Schema grounding.* The model is given the relevant part of a schema catalog (`meta.schema_catalog`, 34 rows) that documents tables, columns and geometry types across the `admin`, `roads`, `transport`, `poi`, `realestate`, `demo`, `crime` and `env` schemas. Grounding on this catalog is what prevents the model from inventing places: it can only reference data that exists. #todo[confirm exactly how schema context is selected and passed to the model, and whether the pipeline has separate agent stages]
+ *Query generation.* The LLM (Groq `openai/gpt-oss-120b`, behind a single client module) writes a PostGIS query using functions such as `ST_DWithin` and `ST_Contains`. All geometry is in EPSG:4326 and indexed with GiST, and every row carries a `city_id`.
+ *Execution.* The query runs on PostgreSQL 16 with PostGIS 3.4.
+ *Result generation.* Rows are converted to a GeoJSON answer layer, and the LLM writes a short explanation grounded in the returned rows. The generated SQL is returned alongside, so users can inspect how the answer was obtained.
+ *Visualization.* The answer layer is drawn on the map next to the base layers. Base layers are served as Mapbox Vector Tiles by Martin directly from PostGIS.

Chat history is stored in MongoDB. It is not used for spatial data.

== Analysis, Framework and Algorithm
=== System Framework Overview
The system has three layers: a presentation layer (React and MapLibre GL), an application layer (FastAPI endpoints and the LLM client), and a data layer (PostGIS, Martin and MongoDB). This separation keeps the model, the query execution and the rendering independently replaceable.

=== Algorithm for Query Processing
```py
def answer(question, city_id):
    schema = schema_context(question)          # from meta.schema_catalog
    sql = llm.generate_sql(question, schema)   # PostGIS, EPSG:4326
    rows = db.execute(sql)                     # GiST-indexed spatial query
    layer = to_geojson(rows)                   # answer layer for the map
    text = llm.explain(question, rows)         # grounded in returned rows
    return layer, text, sql                    # SQL returned as provenance
```

This is a single pass. If the generated query fails or returns no rows, the failure is reported to the user. Self-repair, as in execution-based review stages @spatialt2s, is future work.

=== Decision Support Models
The decision tools are built on the same database and exposed as separate endpoints (`/site-eval`, `/competitor-analysis`, `/business-estimate`).

*Site evaluation.* For a clicked point and a radius between 0.5 and 3 km, the report gives the median price per sqft of nearby listings, a typical price band, a comparison with the city median, a breakdown by size band, the nearest metro, rail and bus stops, amenity counts (healthcare, education, food, banking, shopping), and a safety score with a risk level.

*Competition and catchment analysis.* The report gives the competitor count, density, nearest competitor and a saturation label, together with a 0 to 100 catchment demand index. It also suggests lower-competition spots, shown as green markers, while competitors are drawn as red dots. #todo[state how the demand index is computed from the data and how the saturation thresholds were chosen]

*Cost-to-open and break-even.* The estimator takes a store area in sqft and returns one-time setup costs, monthly running costs, staff cost and working capital. Rent is estimated from nearby sale prices, because rental data is not yet available. Line items are produced by the LLM, with a heuristic fallback when the LLM is unavailable. A revenue and break-even model gives revenue, profit and payback under three scenarios, and the plan can be downloaded or printed. #todo[state the sale-price to rent conversion and the three scenario assumptions]

*Location comparison.* Up to three pinned spots (A, B, C) are shown side by side across price, access, safety, competitors, rent, start-up cost, revenue, profit and payback. The best value in each row is marked.

*Area-level weighted ranking (legacy dashboard).* The original dashboard ranks areas with a standard weighted-sum MCDA model @malczewski. For area $i$ with normalised criteria $hat(m)_(i k)$ (footfall, youth, rent, access, competition, flood risk and traffic),

$ S_i = sum_(k=1)^K w_k thin hat(m)_(i k), quad sum_(k=1)^K w_k = 1, $

where criteria for which lower is better (for example competition or flood risk) are inverted after min-max normalisation. In the POC the metrics were synthetic and the weights fixed by hand. A weight study in the `eval/` folder examines how sensitive the ranking is to the weights. #todo[add the design and results of the weight study]

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
  columns: (auto, auto, 1fr),
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
The database holds all layers in EPSG:4326 with GiST indexes, and every row is tagged with a `city_id` so several cities can coexist. The schema catalog documents the tables for the model.

==== ETL
The ETL pipeline (`etl/`) ingests roads, transit, POIs and boundaries from OSM with polygon-based extraction, geocodes real-estate localities with Nominatim, and loads crime data. Because extraction is driven by a city polygon, the same pipeline can load other cities. The deployed instance is pre-loaded for Mumbai.

==== Legacy Dashboard
The `/dashboard` page is the original assistant view: a chat assistant that asks clarifying questions and ranks areas, a Leaflet map with a heatmap by factor, a Top Locations panel with explanations, and a location detail view. Where an area has no scored metrics, the detail view borrows them from the nearest scored area. We keep it as the baseline against which the Sentinel workspace is compared.

=== Design Considerations
- Verifiability: the SQL is always shown, and answers come from executed queries.
- Performance: vector tiles and spatial indexes keep map interaction fast.
- Generality: the `city_id` tag and polygon-based ETL support other cities.
- Cost efficiency: the stack uses open-source tools and open data.

== Implementation Plan

#table(
  columns: (auto, auto, auto, auto),
  inset: 3pt,
  align: horizon,
  fill: (x, y) => if y == 0 { silver } else { none },
  stroke: 0.5pt + gray,

  [*Phase\ No.*], [*Phase\ Name*], [*Duration*], [*Activities\ Involved*],

  [1], [Requirement Analysis], [Week 1], [Understanding project objectives, identifying system requirements, and defining scope],
  [2], [System Design], [Week 2], [Designing architecture and selecting technologies],
  [3], [Data Collection & Setup], [Week 3], [Downloading OpenStreetMap data, setting up PostgreSQL + PostGIS],
  [4], [Backend Development], [Week 4 to 5], [Developing APIs using FastAPI, integrating database connectivity],
  [5], [Query Engine Development], [Week 6 to 7], [Building the LLM-based natural-language to PostGIS engine and testing spatial operations],
  [6], [Frontend Development], [Week 8 to 9], [Building the React interface with MapLibre GL and vector-tile layers],
  [7], [Decision Tools], [Week 10], [Implementing site evaluation, competition analysis and cost-to-open],
  [8], [Integration & Testing], [Week 11], [Integrating all modules and system testing],
  [9], [Deployment], [Week 12], [Deployment and final validation],
  [10], [Documentation & Report], [Week 13], [Preparing final report, diagrams and presentation]
)

The plan covers about 13 weeks. #todo[confirm this schedule matches the actual timeline, since the architecture changed from the original plan]

== Advantages And Limitation

=== Advantages
+ *Verifiable answers.* Results come from executed queries on real data, and the SQL is shown, which addresses the hallucination problem of direct LLM answers.
+ *Natural-language interface.* Users need no SQL or GIS knowledge.
+ *Decision support.* Site evaluation, competition analysis, cost-to-open and comparison turn a map into a practical planning tool.
+ *Open and low cost.* The stack uses open-source software and open data.
+ *Generalisable.* Polygon-based ETL and `city_id` tagging allow other cities to be added.

=== Limitations
+ *No labelled benchmark.* We have not measured NL to SQL accuracy, so no accuracy claim is made.
+ *No repair loop.* A failing or empty query is not retried automatically.
+ *Limited SQL safeguards.* A dedicated read-only validator for generated SQL is not yet in place. Restricting the database role and validating statements are planned.
+ *No real rental data.* Rent is estimated from sale prices, so cost-to-open figures are approximate.
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

== Evaluation Status

The following measurements have not been made and are required before quantitative claims can be added. We deliberately leave them as open items.

#table(
  columns: (1fr, 1fr),
  inset: 3pt,
  stroke: 0.5pt + gray,
  fill: (x, y) => if y == 0 { silver } else { none },
  [*Measurement*], [*Status*],
  [NL to SQL execution accuracy on a labelled benchmark of spatial questions], [Not built. #todo[build benchmark and report accuracy]],
  [Effect of an execution-based repair stage], [Repair loop not built],
  [Latency of `/nlquery` and the decision endpoints], [#todo[measure median and 95th percentile]],
  [Weight sensitivity of area ranking], [Study exists in `eval/`. #todo[report results]],
  [Accuracy of rent estimate against real rents], [No rental data yet],
)

== Discussion

Grounding the model in a documented schema and returning the executed SQL changes the nature of the interface: answers can be checked, reproduced and corrected. The decision tools show that the same data supports practical questions, such as comparing three candidate shop locations on price, access, safety and competition.

The main weakness of the current work is evaluation. Without a labelled benchmark we cannot say how often the generated SQL is correct, and without a repair stage or a read-only validator we cannot yet claim robustness or safety against malformed or hostile queries. Cost and revenue estimates inherit the approximations in the rent model and the LLM-produced line items, and should be treated as planning aids.

= Conclusion And Future Scope

== Conclusion

GeoQuery Sentinel shows that a natural-language interface to geospatial data can be built so that answers are computed on real data and are inspectable. By pairing a schema-grounded LLM with PostGIS, vector tiles and open data, it avoids the invented places and coordinates of direct LLM answers, and it extends the query engine with site evaluation, competition analysis, cost-to-open modelling and location comparison for practical decisions. The system is functional for Mumbai, and its ETL is designed to generalise. Quantitative evaluation of query accuracy remains to be done.

== Future Scope
+ *Query reliability:* add an execution-based repair loop @spatialt2s and a labelled NL to SQL benchmark in the style of Spider and BIRD @spider @bird.
+ *Safety:* enforce read-only execution through a restricted database role and statement validation.
+ *Data:* integrate real rental data, and extend the metrics modelling with LLM and OSM features where ground truth is scarce @geollm.
+ *Analysis:* replace radius catchments with isochrones.
+ *Usability:* saved sites and a mobile layout.
+ *Coverage:* load additional cities using the existing ETL.

#bibliography("refs.bib", full: false)