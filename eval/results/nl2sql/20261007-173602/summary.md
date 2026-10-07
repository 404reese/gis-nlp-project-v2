# NL to PostGIS benchmark - 20261007-173602
model `openai/gpt-oss-120b`, temperature None, 1 run(s), 39 questions, city_id 1.

## Engine configurations

| config | n | exact | geom F1 | name F1 | executed | non-empty | clarified | mean attempts | LLM calls | median s | p95 s |
|---|---|---|---|---|---|---|---|---|---|---|---|
| full | 39 | 74.4% | 88.4% | 93.2% | 100.0% | 100.0% | 0.0% | 1.00 | 1.00 | 4.5 | 13.8 |
| no_repair | 39 | 74.4% | 88.4% | 93.2% | 100.0% | 100.0% | 0.0% | 1.00 | 0.00 | n/a | n/a |

## Execution accuracy by question category

| config | area | compositional | filter | listing | proximity | ranking |
|---|---|---|---|---|---|---|
| full | 100.0% | 66.7% | 70.0% | 25.0% | 77.8% | 100.0% |
| no_repair | 100.0% | 66.7% | 70.0% | 25.0% | 77.8% | 100.0% |

## Direct-LLM baseline (no database)

| n | names that exist in the DB | points within 150 m of a real feature | points within 200 m of a gold feature | median s |
|---|---|---|---|---|
| 39 | 19.5% | 57.0% | 10.6% | 13.2 |

The baseline returns no SQL, so its answers cannot be checked or reproduced.

## `full` failures (inspect these; some may be valid alternative queries)

| id | executed | n_pred | n_gold | geom F1 | attempts |
|---|---|---|---|---|---|
| F05 | True | 197 | 31 | 27.2% | 1 |
| F07 | True | 499 | 1632 | 46.8% | 1 |
| F10 | True | 236 | 98 | 58.7% | 1 |
| P02 | True | 314 | 946 | 49.8% | 1 |
| P03 | True | 256 | 512 | 66.7% | 1 |
| L02 | True | 500 | 1245 | 57.3% | 1 |
| L03 | True | 500 | 3589 | 24.5% | 1 |
| L04 | True | 500 | 3348 | 26.0% | 1 |
| C04 | True | 28 | 35 | 88.9% | 1 |
| C05 | True | 499 | 500 | 99.9% | 1 |

`no_repair` is derived from the first attempt of each `full` run (paired comparison, no extra LLM calls), so it has no latency of its own.