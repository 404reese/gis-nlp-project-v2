# PostGIS + pgvector.
# Base image already bundles PostGIS 3.4 + raster on Postgres 16 and configures the
# PGDG apt repo, so pgvector installs cleanly from the package index.
FROM postgis/postgis:16-3.4

RUN apt-get update \
    && apt-get install -y --no-install-recommends postgresql-16-pgvector \
    && rm -rf /var/lib/apt/lists/*
