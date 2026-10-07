"""Benchmark + ablation for the NL -> PostGIS engine (and a direct-LLM baseline).

Configurations
  full               the engine as shipped: intent check, schema description, validation,
                     read-only execution, repair loop (<=2 repairs + 1 empty-result loosening)
  no_repair          same, but a single generation attempt (repair stage off)
  table_names_only   same as `full`, but the schema description lists only table names
                     (no columns, enum values or grounding hints); the rules block is kept
  direct_llm         the POC approach: the LLM names places and coordinates, no database

Scoring (engine configs): the predicted answer layer is compared with the answer layer of the
gold query, both EXECUTED on the database. Features are compared by geometry (rounded to 5
decimals, ~1 m), so the model's column names do not matter.
  exact      predicted geometry set == gold geometry set          (execution accuracy)
  f1         F1 of the two geometry sets
  name_f1    F1 of the `name` property sets, when both layers carry names (lenient metric)
Scoring (direct_llm): no SQL exists, so it is scored on grounding instead:
  name_grounded   share of returned names that exist in the database (ILIKE match)
  coord_grounded  share of returned points within 150 m of a real POI / stop / gazetteer point
  precision_gold  share of returned points within 200 m of a gold feature

Usage (from the repo root, with the app's venv, which has sqlalchemy/asyncpg/requests):
  app\\venv\\Scripts\\python eval\\nl2sql\\run_benchmark.py --lint              # no DB, no LLM
  app\\venv\\Scripts\\python eval\\nl2sql\\run_benchmark.py --validate-gold      # DB only, no LLM
  app\\venv\\Scripts\\python eval\\nl2sql\\run_benchmark.py --configs full no_repair --runs 3
Needs GROQ_API_KEY (via app/config.py) for anything that calls the LLM.
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import json
import math
import re
import statistics
import sys
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from questions import QUESTIONS  # noqa: E402

OUT_ROOT = ROOT / "eval" / "results" / "nl2sql"
ENGINE_CONFIGS = ["full", "no_repair", "table_names_only"]
ALL_CONFIGS = ENGINE_CONFIGS + ["direct_llm"]
DEFAULT_MODEL = "openai/gpt-oss-120b"
CITY_ID = 1


# ───────────────────────────── LLM wrapper (shared by every config) ─────────────────────────────
class LLM:
    """Same chat-completions call as app/services/groq_client.py, with the model selectable,
    optional fixed temperature, retries on rate limits, and a call counter."""

    def __init__(self, model: str, temperature: float | None, sleep: float):
        from app.config import settings
        self.key = settings.GROQ_API_KEY
        self.model, self.temperature, self.sleep = model, temperature, sleep
        self.calls = 0

    def __call__(self, prompt: str) -> str:
        import requests
        payload = {"model": self.model, "messages": [{"role": "user", "content": prompt}]}
        if self.temperature is not None:
            payload["temperature"] = self.temperature
        for attempt in range(5):
            r = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"},
                json=payload, timeout=120,
            )
            if r.status_code == 429 or r.status_code >= 500:
                time.sleep(min(2 ** attempt * 2, 30))
                continue
            r.raise_for_status()
            self.calls += 1
            time.sleep(self.sleep)
            return r.json()["choices"][0]["message"]["content"]
        r.raise_for_status()
        raise RuntimeError("LLM call failed after retries")


# ───────────────────────────────────── geometry comparison ─────────────────────────────────────
def _round(c):
    return round(c, 5) if isinstance(c, (int, float)) else [_round(x) for x in c]


def geom_key(feature: dict):
    g = feature.get("geometry")
    if not g or "coordinates" not in g:
        return None
    return g["type"] + json.dumps(_round(g["coordinates"]), separators=(",", ":"))


def geom_set(fc: dict) -> set:
    return {k for k in (geom_key(f) for f in fc.get("features", [])) if k}


def name_set(fc: dict) -> set:
    out = set()
    for f in fc.get("features", []):
        n = (f.get("properties") or {}).get("name")
        if n:
            out.add(str(n).strip().lower())
    return out


def prf(pred: set, gold: set) -> tuple[float, float, float]:
    if not pred or not gold:
        return 0.0, 0.0, 0.0
    tp = len(pred & gold)
    p, r = tp / len(pred), tp / len(gold)
    return p, r, (2 * p * r / (p + r) if p + r else 0.0)


def _ordered_keys(fc: dict) -> list:
    seen, out = set(), []
    for f in fc.get("features", []):
        k = geom_key(f)
        if k and k not in seen:
            seen.add(k)
            out.append(k)
    return out


def score_engine(pred_fc: dict | None, gold_fc: dict, ordered: bool) -> dict:
    if pred_fc is None:
        return dict(exact=False, f1=0.0, precision=0.0, recall=0.0, name_f1=None, ordered_match=None,
                    n_pred=0)
    pg, gg = geom_set(pred_fc), geom_set(gold_fc)
    p, r, f1 = prf(pg, gg)
    pn, gn = name_set(pred_fc), name_set(gold_fc)
    name_f1 = prf(pn, gn)[2] if pn and gn else None
    om = None
    if ordered:
        om = _ordered_keys(pred_fc)[: len(_ordered_keys(gold_fc))] == _ordered_keys(gold_fc)
    return dict(exact=pg == gg and bool(gg), f1=f1, precision=p, recall=r, name_f1=name_f1,
                ordered_match=om, n_pred=len(pg))


# ───────────────────────────────────────── gold results ─────────────────────────────────────────
async def fetch_gold(ge, q: dict) -> tuple[dict | None, str | None]:
    try:
        sql = ge.validate_select(q["gold"])
        fc, _ = await ge._execute_to_geojson(sql, CITY_ID)
        return fc, None
    except Exception as exc:  # noqa: BLE001
        return None, str(exc).split("\n")[0][:300]


# ───────────────────────────────────────── engine configs ─────────────────────────────────────────
@contextmanager
def patched(module, **attrs):
    old = {k: getattr(module, k) for k in attrs}
    for k, v in attrs.items():
        setattr(module, k, v)
    try:
        yield
    finally:
        for k, v in old.items():
            setattr(module, k, v)


def config_patches(ge, name: str, llm: LLM) -> dict:
    patches = {"call_groq": llm}
    if name == "no_repair":
        patches["MAX_REPAIRS"] = -1  # loop runs range(MAX_REPAIRS + 2) = 1 attempt
    elif name == "table_names_only":
        rules = ge.SCHEMA_DOC[ge.SCHEMA_DOC.index("RULES:"):]
        patches["SCHEMA_DOC"] = (
            "All tables are in PostGIS, geometry column is `geom`, SRID 4326. Every feature table has\n"
            "`city_id` — ALWAYS filter `city_id = :CITY_ID` on every table you read.\n\n"
            "Tables: admin.boundary, roads.segment, transport.stop, poi.place, realestate.listing,\n"
            "demo.cell, crime.area, env.measurement\n\n" + rules
        )
    return patches


async def run_engine(ge, name: str, q: dict, gold_fc: dict, llm: LLM) -> dict:
    calls0, t0 = llm.calls, time.perf_counter()
    with patched(ge, **config_patches(ge, name, llm)):
        res = await ge.run_nl_query(q["question"], CITY_ID)
    latency = time.perf_counter() - t0
    attempts = res.get("attempts") or []
    pred = res.get("answer") if res.get("ok") else None
    rec = dict(
        executed=bool(res.get("ok")),
        clarified=not res.get("is_clear", True),
        non_empty=bool(res.get("count")),
        attempts=len(attempts),
        failed_attempts=sum(1 for a in attempts if a.get("error")),
        sql=res.get("sql"),
        message=(res.get("message") or "")[:200],
    )
    rec.update(score_engine(pred, gold_fc, q["ordered"]))
    rec.update(llm_calls=llm.calls - calls0, latency_s=round(latency, 2))
    return rec


# ───────────────────────────────────────── direct-LLM baseline ─────────────────────────────────────────
def _centre(geom: dict):
    pts = []

    def walk(c):
        if c and isinstance(c[0], (int, float)):
            pts.append(c)
        else:
            for x in c:
                walk(x)
    walk(geom["coordinates"])
    if not pts:
        return None
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return (min(ys) + max(ys)) / 2, (min(xs) + max(xs)) / 2  # lat, lon


def _haversine_m(a, b) -> float:
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * 6371000 * math.asin(math.sqrt(h))


async def run_direct(ge, q: dict, gold_fc: dict, llm: LLM) -> dict:
    from sqlalchemy import text
    from app.db_spatial import get_engine

    prompt = f"""You are a geospatial assistant for Mumbai, India.
Answer the question by listing up to 20 specific real places that match it.

Question: "{q['question']}"

Return STRICT JSON only:
{{"places": [{{"name": "string", "lat": 0.0, "lon": 0.0}}]}}"""
    calls0, t0 = llm.calls, time.perf_counter()
    try:
        data = ge.parse_json_safely(llm(prompt))
        places = [p for p in data.get("places", []) if isinstance(p, dict)]
    except Exception:  # noqa: BLE001
        places = []
    latency = time.perf_counter() - t0

    gold_pts = [c for c in (_centre(f["geometry"]) for f in gold_fc.get("features", [])
                            if f.get("geometry")) if c]
    name_ok = coord_ok = prec_ok = valid = 0
    eng = get_engine()
    async with eng.connect() as conn:
        for p in places:
            try:
                lat, lon, name = float(p["lat"]), float(p["lon"]), str(p.get("name", "")).strip()
            except (KeyError, TypeError, ValueError):
                continue
            valid += 1
            if len(name) >= 3:
                hit = (await conn.execute(text(
                    """SELECT EXISTS (SELECT 1 FROM poi.place WHERE city_id=:c AND name ILIKE :n)
                          OR EXISTS (SELECT 1 FROM crime.area WHERE city_id=:c AND name ILIKE :n)
                          OR EXISTS (SELECT 1 FROM transport.stop WHERE city_id=:c AND name ILIKE :n)
                          OR EXISTS (SELECT 1 FROM admin.boundary WHERE city_id=:c AND name ILIKE :n)"""
                ), {"c": CITY_ID, "n": f"%{name}%"})).scalar()
                name_ok += bool(hit)
            near = (await conn.execute(text(
                """SELECT EXISTS (SELECT 1 FROM poi.place WHERE city_id=:c AND ST_DWithin(
                          geom::geography, ST_SetSRID(ST_MakePoint(:lon,:lat),4326)::geography, 150))
                      OR EXISTS (SELECT 1 FROM transport.stop WHERE city_id=:c AND ST_DWithin(
                          geom::geography, ST_SetSRID(ST_MakePoint(:lon,:lat),4326)::geography, 150))
                      OR EXISTS (SELECT 1 FROM crime.area WHERE city_id=:c AND ST_DWithin(
                          geom::geography, ST_SetSRID(ST_MakePoint(:lon,:lat),4326)::geography, 150))"""
            ), {"c": CITY_ID, "lat": lat, "lon": lon})).scalar()
            coord_ok += bool(near)
            prec_ok += any(_haversine_m((lat, lon), g) <= 200 for g in gold_pts)
    n = valid or 1
    return dict(
        executed=bool(places), clarified=False, non_empty=bool(places), attempts=1, failed_attempts=0,
        sql=None, message="", exact=None, f1=None, precision=None, recall=None, name_f1=None,
        ordered_match=None, n_pred=valid,
        name_grounded=name_ok / n if valid else 0.0,
        coord_grounded=coord_ok / n if valid else 0.0,
        precision_gold=prec_ok / n if valid else 0.0,
        llm_calls=llm.calls - calls0, latency_s=round(latency, 2),
    )


# ───────────────────────────────────────── modes ─────────────────────────────────────────
def cmd_lint() -> int:
    """Static checks that need neither the database nor the LLM."""
    sys.path.insert(0, str(ROOT))
    import app.services.geo_engine as ge
    bad = 0
    for q in QUESTIONS:
        problems = []
        try:
            sql = ge.validate_select(q["gold"])
        except ValueError as exc:
            problems.append(f"validate_select: {exc}")
            sql = q["gold"]
        low = sql.lower()
        if " geom" not in low and "geom," not in low and ".geom" not in low:
            problems.append("no geom column")
        n_tables = len(re.findall(r"\b(?:from|join)\s+[a-z_]+\.[a-z_]+", low))
        n_city = len(re.findall(r"city_id\s*=\s*1", low))
        if n_city < n_tables:
            problems.append(f"city_id filter on {n_city} of {n_tables} tables")
        if problems:
            bad += 1
            print(f"{q['id']}: " + "; ".join(problems))
    print(f"{len(QUESTIONS)} questions linted, {bad} with problems.")
    return 1 if bad else 0


async def cmd_validate_gold() -> int:
    import app.services.geo_engine as ge
    from app.db_spatial import dispose_engines
    bad = 0
    try:
        for q in QUESTIONS:
            fc, err = await fetch_gold(ge, q)
            n = len(fc["features"]) if fc else 0
            flag = ""
            if err:
                flag, bad = f"ERROR {err}", bad + 1
            elif n == 0:
                flag, bad = "EMPTY - fix or drop", bad + 1
            elif n >= ge.MAX_FEATURES:
                flag, bad = "HIT ROW CAP - result truncated", bad + 1
            elif n == 1:
                flag = "only 1 row - weak test"
            print(f"{q['id']} {q['category']:<13} rows={n:<5} {flag}")
    finally:
        await dispose_engines()
    print(f"\n{len(QUESTIONS)} gold queries, {bad} need attention.")
    return 1 if bad else 0


async def cmd_run(args) -> int:
    import app.services.geo_engine as ge
    from app.db_spatial import dispose_engines

    questions = [q for q in QUESTIONS if not args.only or q["id"] in args.only]
    if args.limit:
        questions = questions[: args.limit]
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out = OUT_ROOT / stamp
    out.mkdir(parents=True, exist_ok=True)
    llm = LLM(args.model, args.temperature, args.sleep)

    meta = dict(timestamp=stamp, model=args.model, temperature=args.temperature, runs=args.runs,
                configs=args.configs, n_questions=len(questions), city_id=CITY_ID)
    (out / "meta.json").write_text(json.dumps(meta, indent=2))

    records, skipped = [], []
    try:
        gold = {}
        for q in questions:
            fc, err = await fetch_gold(ge, q)
            if err or not fc or not fc["features"]:
                skipped.append({"id": q["id"], "reason": err or "gold query returned no rows"})
                continue
            gold[q["id"]] = fc
        if skipped:
            print("Skipping questions with unusable gold:", ", ".join(s["id"] for s in skipped))
        (out / "skipped.json").write_text(json.dumps(skipped, indent=2))

        total = len(gold) * len(args.configs) * args.runs
        done = 0
        with open(out / "raw.jsonl", "w", encoding="utf-8") as raw:
            for run in range(args.runs):
                for cfg in args.configs:
                    for q in questions:
                        if q["id"] not in gold:
                            continue
                        try:
                            rec = (await run_direct(ge, q, gold[q["id"]], llm) if cfg == "direct_llm"
                                   else await run_engine(ge, cfg, q, gold[q["id"]], llm))
                        except Exception as exc:  # noqa: BLE001 - one bad call must not kill the run
                            rec = dict(executed=False, clarified=False, non_empty=False, attempts=0,
                                       failed_attempts=0, sql=None, message=f"runner error: {exc}"[:200],
                                       exact=False if cfg != "direct_llm" else None, f1=0.0 if cfg != "direct_llm" else None,
                                       latency_s=None, llm_calls=0)
                        rec.update(config=cfg, qid=q["id"], category=q["category"],
                                   difficulty=q["difficulty"], run=run, n_gold=len(geom_set(gold[q["id"]])))
                        records.append(rec)
                        raw.write(json.dumps(rec, ensure_ascii=False) + "\n")
                        raw.flush()
                        done += 1
                        print(f"[{done}/{total}] {cfg:<17} {q['id']} run{run} "
                              f"exact={rec.get('exact')} f1={rec.get('f1')}")
    finally:
        await dispose_engines()

    write_summary(out, records, meta)
    print(f"\nResults in {out}")
    return 0


# ───────────────────────────────────────── summary ─────────────────────────────────────────
def _mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def _pct(x):
    return "n/a" if x is None else f"{100 * x:.1f}%"


def _p95(xs):
    xs = sorted(x for x in xs if x is not None)
    return xs[min(len(xs) - 1, math.ceil(0.95 * len(xs)) - 1)] if xs else None


def write_summary(out: Path, records: list[dict], meta: dict) -> None:
    configs = [c for c in ALL_CONFIGS if any(r["config"] == c for r in records)]
    cats = sorted({r["category"] for r in records})

    rows = []
    for c in configs:
        rs = [r for r in records if r["config"] == c]
        lat = [r["latency_s"] for r in rs]
        rows.append(dict(
            config=c, n=len(rs),
            exact=_mean([r["exact"] for r in rs if r["exact"] is not None]),
            f1=_mean([r["f1"] for r in rs]),
            name_f1=_mean([r["name_f1"] for r in rs]),
            executed=_mean([r["executed"] for r in rs]),
            non_empty=_mean([r["non_empty"] for r in rs]),
            clarified=_mean([r["clarified"] for r in rs]),
            attempts=_mean([r["attempts"] for r in rs]),
            llm_calls=_mean([r["llm_calls"] for r in rs]),
            lat_med=statistics.median([x for x in lat if x is not None]) if any(x is not None for x in lat) else None,
            lat_p95=_p95(lat),
            name_grounded=_mean([r.get("name_grounded") for r in rs]),
            coord_grounded=_mean([r.get("coord_grounded") for r in rs]),
            precision_gold=_mean([r.get("precision_gold") for r in rs]),
        ))

    with open(out / "summary.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else [])
        w.writeheader()
        w.writerows(rows)

    md = [f"# NL to PostGIS benchmark - {meta['timestamp']}",
          f"model `{meta['model']}`, temperature {meta['temperature']}, {meta['runs']} run(s), "
          f"{meta['n_questions']} questions, city_id {meta['city_id']}.\n",
          "## Engine configurations\n",
          "| config | n | exact | geom F1 | name F1 | executed | non-empty | clarified | mean attempts | LLM calls | median s | p95 s |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        if r["config"] == "direct_llm":
            continue
        md.append(f"| {r['config']} | {r['n']} | {_pct(r['exact'])} | {_pct(r['f1'])} | {_pct(r['name_f1'])} | "
                  f"{_pct(r['executed'])} | {_pct(r['non_empty'])} | {_pct(r['clarified'])} | "
                  f"{r['attempts']:.2f} | {r['llm_calls']:.2f} | {r['lat_med']:.1f} | {r['lat_p95']:.1f} |")

    md += ["\n## Execution accuracy by question category\n",
           "| config | " + " | ".join(cats) + " |", "|---|" + "---|" * len(cats)]
    for c in configs:
        if c == "direct_llm":
            continue
        cells = []
        for cat in cats:
            xs = [r["exact"] for r in records if r["config"] == c and r["category"] == cat]
            cells.append(_pct(_mean(xs)))
        md.append(f"| {c} | " + " | ".join(cells) + " |")

    d = next((r for r in rows if r["config"] == "direct_llm"), None)
    if d:
        md += ["\n## Direct-LLM baseline (no database)\n",
               "| n | names that exist in the DB | points within 150 m of a real feature | "
               "points within 200 m of a gold feature | median s |", "|---|---|---|---|---|",
               f"| {d['n']} | {_pct(d['name_grounded'])} | {_pct(d['coord_grounded'])} | "
               f"{_pct(d['precision_gold'])} | {d['lat_med']:.1f} |",
               "\nThe baseline returns no SQL, so its answers cannot be checked or reproduced."]

    failures = [r for r in records if r["config"] == "full" and not r.get("exact")]
    if failures:
        md += ["\n## `full` failures (inspect these; some may be valid alternative queries)\n",
               "| id | executed | n_pred | n_gold | geom F1 | attempts |", "|---|---|---|---|---|---|"]
        for r in failures:
            md.append(f"| {r['qid']} | {r['executed']} | {r.get('n_pred')} | {r['n_gold']} | "
                      f"{_pct(r.get('f1'))} | {r['attempts']} |")
    (out / "summary.md").write_text("\n".join(md), encoding="utf-8")

    # Typst table for the paper
    eng = [r for r in rows if r["config"] != "direct_llm"]
    label = {"full": "Full engine", "no_repair": "No repair stage", "table_names_only": "Table names only"}
    typ = ["#table(", "  columns: (1fr, auto, auto, auto, auto),", "  inset: 3pt,",
           "  stroke: 0.5pt + gray,", "  fill: (x, y) => if y == 0 { silver } else { none },",
           "  [*Configuration*], [*Exact*], [*Geom. F1*], [*Executed*], [*Median s*],"]
    for r in eng:
        typ.append(f"  [{label.get(r['config'], r['config'])}], [{_pct(r['exact'])}], [{_pct(r['f1'])}], "
                   f"[{_pct(r['executed'])}], [{r['lat_med']:.1f}],")
    typ.append(")")
    (out / "paper_table.typ").write_text("\n".join(typ), encoding="utf-8")

    from plots import make_plots
    charts = make_plots(out, records)
    if charts:
        print("Charts:", ", ".join(charts))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--lint", action="store_true", help="static checks of the gold SQL (no DB, no LLM)")
    ap.add_argument("--validate-gold", action="store_true", help="run gold SQL on the DB (no LLM)")
    ap.add_argument("--configs", nargs="+", default=ENGINE_CONFIGS + ["direct_llm"], choices=ALL_CONFIGS)
    ap.add_argument("--runs", type=int, default=1, help="repeat everything N times (the LLM is nondeterministic)")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--temperature", type=float, default=None, help="fix the LLM temperature (default: API default)")
    ap.add_argument("--sleep", type=float, default=0.5, help="pause after each LLM call (rate limits)")
    ap.add_argument("--only", nargs="+", help="question ids to run, e.g. F01 P02")
    ap.add_argument("--limit", type=int, help="run only the first N questions (smoke test)")
    args = ap.parse_args()

    if args.lint:
        return cmd_lint()
    if args.validate_gold:
        return asyncio.run(cmd_validate_gold())
    return asyncio.run(cmd_run(args))


if __name__ == "__main__":
    raise SystemExit(main())
