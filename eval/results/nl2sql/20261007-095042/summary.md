# NL to PostGIS benchmark - 20261007-095042
model `openai/gpt-oss-120b`, temperature None, 1 run(s), 3 questions, city_id 1.

## Engine configurations

| config | n | exact | geom F1 | name F1 | executed | non-empty | clarified | mean attempts | LLM calls | median s | p95 s |
|---|---|---|---|---|---|---|---|---|---|---|---|
| full | 3 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 0.0% | 1.00 | 3.00 | 4.6 | 4.9 |

## Execution accuracy by question category

| config | filter |
|---|---|
| full | 100.0% |

## Direct-LLM baseline (no database)

| n | names that exist in the DB | points within 150 m of a real feature | points within 200 m of a gold feature | median s |
|---|---|---|---|---|
| 3 | 18.3% | 75.0% | 8.3% | 4.6 |

The baseline returns no SQL, so its answers cannot be checked or reproduced.