-- Extensions. Runs once, on first container init (empty data volume).
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_raster;
CREATE EXTENSION IF NOT EXISTS vector;      -- pgvector, for schema-catalog retrieval
CREATE EXTENSION IF NOT EXISTS pg_trgm;     -- fuzzy text matching on names/localities
