# NL → PostGIS benchmark

Measures the query engine (`app/services/geo_engine.py`) against hand-written gold queries, and
compares it with ablations and with the direct-LLM approach of the proof of concept.
Feeds the paper's evaluation section (execution accuracy, effect of the repair stage,
hallucination of the direct-LLM baseline, latency).

## What is in here

| file | purpose |
|---|---|
| `questions.py` | 39 questions with gold SQL: filter (10), proximity (9), named area (7), ranking (3), listings (4), compositional (6) |
| `run_benchmark.py` | runner, scorer, summary writer |

Results go to `eval/results/nl2sql/<timestamp>/`: `raw.jsonl` (one line per question × config × run,
including the predicted SQL), `summary.md`, `summary.csv`, `paper_table.typ`, `meta.json`, `skipped.json`,
and four column-width bar charts (`bench_accuracy.png`, `bench_by_category.png`, `bench_baseline.png`,
`bench_latency.png`, from `plots.py`; skipped if matplotlib is missing). Copy the charts and
`paper_table.typ` into `paper-publication/` and fill the TODO in the "Comparative Analysis" section.
The charts have only been tested on synthetic records, so check the first real ones by eye.

## Configurations

| config | what changes |
|---|---|
| `full` | the engine as shipped (intent check, schema description, validation, read-only execution, repair) |
| `no_repair` | one generation attempt only |
| `table_names_only` | schema description reduced to table names; the rules block is kept |
| `direct_llm` | POC baseline: the LLM lists places and coordinates, no database |

A model comparison is `--model <groq model id>` run once per model.

## Metrics

Engine configs: the predicted answer layer is compared with the gold answer layer, both executed on
the database, by geometry rounded to 5 decimals (column names are ignored).
`exact` = same geometry set (execution accuracy); `geom F1`; `name F1` (lenient, only when both sides
carry names); executed / non-empty / clarification rate; attempts; LLM calls; latency.

`direct_llm` has no SQL, so it is scored on grounding: share of returned names that exist in the
database, share of points within 150 m of a real feature, share within 200 m of a gold feature.

## Run it

Use the app's venv from the repo root (needs the database for everything except `--lint`, and
`GROQ_API_KEY` for anything that calls the LLM).

```bash
app\venv\Scripts\python eval\nl2sql\run_benchmark.py --lint            # static check of the gold SQL, no DB/LLM
app\venv\Scripts\python eval\nl2sql\run_benchmark.py --validate-gold   # runs gold SQL on the DB, no LLM
app\venv\Scripts\python eval\nl2sql\run_benchmark.py --limit 3 --configs full   # smoke test
app\venv\Scripts\python eval\nl2sql\run_benchmark.py --runs 3          # full benchmark
```

Run `--validate-gold` first and fix or drop any gold query it flags (error, empty, truncated at the
5,000-row cap). The runner skips questions whose gold result is unusable and lists them in
`skipped.json`. A full run makes roughly 39 × (about 3 calls per engine config + 1 for the baseline)
× runs LLM calls; use `--sleep` if you hit rate limits.

## Running on a free API tier

* By default the runner skips the intent-check and explanation LLM calls (they do not change the SQL),
  so each question costs 1 call plus repairs. `--full-pipeline` turns them back on.
* `no_repair` is **derived** from the first attempt of each `full` run (the SQL is re-executed on the
  database), so it costs no LLM calls and is a paired comparison.
* `--max-calls N` stops cleanly after N LLM calls; a hit API quota also stops the run cleanly. Everything
  finished is saved. Continue with `--resume <results folder>` (same `--configs`) the next day.
* Suggested order: `--configs full no_repair` (about 45 calls), then `--configs direct_llm` (39), then
  `--configs table_names_only` (39 or more because it triggers more repairs), each with `--resume`.
* `--summarize-only <folder>` rebuilds the summary and charts from saved results (no DB, no LLM), so the
  charts can be drawn with any Python that has matplotlib.

## Status and caveats

* The gold SQL has been **linted** (single read-only SELECT, `geom` column, `city_id` filter on every
  table) but **not executed against the data**: the database was not running when this was written.
  Treat `--validate-gold` as the first step.
* The runner has been tested offline with synthetic records only; no benchmark numbers exist yet.
* The LLM is called without a fixed temperature by default, so repeat with `--runs 3` or more and
  report the spread. `--temperature 0` is available for a deterministic comparison.
* "In <area>" questions use the engine's documented convention (within 2 km of a gazetteer area).
  An alternative radius is a legitimate reading but scores as wrong; this is stated in the paper's
  limitations, not hidden here.
* Ranking cut-offs avoid ties in `app/data/crime.json` (checked against the weight-study score table).
  Re-check if the crime data changes.
* Listing questions return locality-level points (listings are geocoded per locality), so many listings
  share one geometry and the geometry set is small. They test filtering, not spatial precision.
* 39 questions is a small benchmark. Report counts, not just percentages, and do not claim
  significance from differences of a few questions.
