-- GeoQuery Sentinel spatial schema (see docs/ARCHITECTURE.md §4).
-- All geometry in EPSG:4326. Metric operations use ST_Transform at query time.
-- Every feature table carries city_id so one database serves many cities.

CREATE SCHEMA IF NOT EXISTS core;
CREATE SCHEMA IF NOT EXISTS admin;
CREATE SCHEMA IF NOT EXISTS roads;
CREATE SCHEMA IF NOT EXISTS transport;
CREATE SCHEMA IF NOT EXISTS poi;
CREATE SCHEMA IF NOT EXISTS realestate;
CREATE SCHEMA IF NOT EXISTS demo;
CREATE SCHEMA IF NOT EXISTS crime;
CREATE SCHEMA IF NOT EXISTS env;
CREATE SCHEMA IF NOT EXISTS meta;

-- ---------------------------------------------------------------------------
-- core
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS core.city (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name        TEXT NOT NULL,
    country     TEXT,
    centroid    geometry(Point, 4326),
    bbox        geometry(Polygon, 4326),
    ingested_at TIMESTAMPTZ,
    status      TEXT NOT NULL DEFAULT 'pending',   -- pending | ingesting | ready | error
    UNIQUE (name, country)
);

-- ---------------------------------------------------------------------------
-- Administrative + Roads / Transport
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS admin.boundary (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    city_id     BIGINT NOT NULL REFERENCES core.city(id) ON DELETE CASCADE,
    name        TEXT,
    admin_level INT,
    kind        TEXT,                              -- city | zone | ward | district
    geom        geometry(MultiPolygon, 4326)
);

CREATE TABLE IF NOT EXISTS roads.segment (
    id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    city_id       BIGINT NOT NULL REFERENCES core.city(id) ON DELETE CASCADE,
    name          TEXT,
    highway_class TEXT,
    maxspeed      INT,
    oneway        BOOLEAN,
    geom          geometry(LineString, 4326)
);

CREATE TABLE IF NOT EXISTS transport.stop (
    id       BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    city_id  BIGINT NOT NULL REFERENCES core.city(id) ON DELETE CASCADE,
    name     TEXT,
    mode     TEXT,                                 -- bus | metro | rail | tram
    geom     geometry(Point, 4326)
);

CREATE TABLE IF NOT EXISTS transport.line (
    id       BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    city_id  BIGINT NOT NULL REFERENCES core.city(id) ON DELETE CASCADE,
    name     TEXT,
    mode     TEXT,
    geom     geometry(LineString, 4326)
);

-- ---------------------------------------------------------------------------
-- Businesses / POIs + Real Estate
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS poi.place (
    id        BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    city_id   BIGINT NOT NULL REFERENCES core.city(id) ON DELETE CASCADE,
    name      TEXT,
    category  TEXT,                                -- restaurant | bank | hospital | store | ...
    tags      JSONB,
    geom      geometry(Point, 4326)
);

CREATE TABLE IF NOT EXISTS realestate.listing (
    id         BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    city_id    BIGINT NOT NULL REFERENCES core.city(id) ON DELETE CASCADE,
    locality   TEXT,
    bhk        INT,
    type       TEXT,
    area_sqft  DOUBLE PRECISION,
    price      DOUBLE PRECISION,
    price_unit TEXT,
    status     TEXT,
    age        TEXT,
    geom       geometry(Point, 4326)
);

-- ---------------------------------------------------------------------------
-- Population / Demographics
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS demo.cell (
    id           BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    city_id      BIGINT NOT NULL REFERENCES core.city(id) ON DELETE CASCADE,
    population   DOUBLE PRECISION,
    density      DOUBLE PRECISION,
    age_median   DOUBLE PRECISION,
    income_index DOUBLE PRECISION,
    source       TEXT,
    geom         geometry(Polygon, 4326)
);

-- ---------------------------------------------------------------------------
-- Crime + Environment
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS crime.incident_agg (
    id        BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    city_id   BIGINT NOT NULL REFERENCES core.city(id) ON DELETE CASCADE,
    zone      TEXT,
    category  TEXT,
    count     INT,
    period    TEXT,
    geom      geometry(MultiPolygon, 4326)
);

CREATE TABLE IF NOT EXISTS env.measurement (
    id       BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    city_id  BIGINT NOT NULL REFERENCES core.city(id) ON DELETE CASCADE,
    kind     TEXT,                                 -- aqi | flood_risk
    value    DOUBLE PRECISION,
    ts       TIMESTAMPTZ,
    geom     geometry(Geometry, 4326)              -- point or polygon depending on kind
);

-- ---------------------------------------------------------------------------
-- meta: schema catalog for NL -> SQL grounding (pgvector retrieval)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS meta.schema_catalog (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    schema_name TEXT NOT NULL,
    table_name  TEXT NOT NULL,
    column_name TEXT NOT NULL,
    data_type   TEXT,
    is_geometry BOOLEAN NOT NULL DEFAULT FALSE,
    description TEXT,
    embedding   vector(768),
    UNIQUE (schema_name, table_name, column_name)
);

-- ---------------------------------------------------------------------------
-- Spatial + lookup indexes
-- ---------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_city_bbox        ON core.city            USING GIST (bbox);
CREATE INDEX IF NOT EXISTS idx_admin_geom       ON admin.boundary       USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_admin_city       ON admin.boundary       (city_id);
CREATE INDEX IF NOT EXISTS idx_roads_geom       ON roads.segment        USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_roads_city       ON roads.segment        (city_id);
CREATE INDEX IF NOT EXISTS idx_tstop_geom       ON transport.stop       USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_tstop_city       ON transport.stop       (city_id);
CREATE INDEX IF NOT EXISTS idx_tline_geom       ON transport.line       USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_poi_geom         ON poi.place            USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_poi_city         ON poi.place            (city_id);
CREATE INDEX IF NOT EXISTS idx_poi_category     ON poi.place            (category);
CREATE INDEX IF NOT EXISTS idx_listing_geom     ON realestate.listing   USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_listing_city     ON realestate.listing   (city_id);
CREATE INDEX IF NOT EXISTS idx_listing_locality ON realestate.listing   USING GIN (locality gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_demo_geom        ON demo.cell            USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_demo_city        ON demo.cell            (city_id);
CREATE INDEX IF NOT EXISTS idx_crime_geom       ON crime.incident_agg   USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_crime_city       ON crime.incident_agg   (city_id);
CREATE INDEX IF NOT EXISTS idx_env_geom         ON env.measurement      USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_env_city         ON env.measurement      (city_id);
