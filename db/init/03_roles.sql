-- Read-only role used by the NL -> SQL engine (defense-in-depth: the LLM-generated
-- SQL runs as this role, so it can never write, drop, or escape the data schemas).
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'geo_readonly') THEN
        CREATE ROLE geo_readonly LOGIN PASSWORD 'geo_readonly';
    END IF;
END
$$;

GRANT CONNECT ON DATABASE geo TO geo_readonly;

GRANT USAGE ON SCHEMA core, admin, roads, transport, poi, realestate, demo, crime, env, meta
    TO geo_readonly;

GRANT SELECT ON ALL TABLES IN SCHEMA
    core, admin, roads, transport, poi, realestate, demo, crime, env, meta
    TO geo_readonly;

-- Future tables created by the owner are auto-granted SELECT to the read-only role.
ALTER DEFAULT PRIVILEGES IN SCHEMA core, admin, roads, transport, poi, realestate, demo, crime, env, meta
    GRANT SELECT ON TABLES TO geo_readonly;
