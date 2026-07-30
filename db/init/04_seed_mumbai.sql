-- Seed the pre-baked city row so the app has something to point at before ETL runs.
-- Real layer data is loaded by the M1 ETL pipeline (etl/); this only reserves the
-- city_id and stores its bounding box / centroid.
INSERT INTO core.city (name, country, centroid, bbox, status)
VALUES (
    'Mumbai',
    'India',
    ST_SetSRID(ST_MakePoint(72.8777, 19.0760), 4326),
    ST_SetSRID(
        ST_MakeEnvelope(72.7750, 18.8900, 72.9900, 19.2800), -- minlon, minlat, maxlon, maxlat
        4326
    ),
    'pending'
)
ON CONFLICT (name, country) DO NOTHING;
