"""Latency of the decision endpoints on a RUNNING backend (for the paper's evaluation table).

Calls /site-eval, /competitor-analysis and /business-estimate a few times at five Mumbai
points and prints median / 95th-percentile seconds as a markdown table. /nlquery latency is
already measured per configuration by eval/nl2sql/run_benchmark.py, so it is not repeated here.

Start the backend first (from the repo root):
    app\\venv\\Scripts\\python -m uvicorn app.main:app --port 8000
Then:
    app\\venv\\Scripts\\python eval\\latency_endpoints.py            # defaults: 5 points x 4 repeats
    app\\venv\\Scripts\\python eval\\latency_endpoints.py --repeats 8 --base http://localhost:8000

/business-estimate calls the LLM, so it is slower and costs API calls; use --skip-business to leave it out.
The first call of each endpoint is a warm-up and is excluded from the statistics.
"""
import argparse
import math
import statistics
import time

import requests

POINTS = [  # name, lat, lng
    ("Bandra", 19.0596, 72.8295),
    ("Andheri", 19.1197, 72.8468),
    ("Powai", 19.1176, 72.9060),
    ("Dadar", 19.0178, 72.8478),
    ("Ghatkopar", 19.0860, 72.9081),
]


def timed(fn):
    t0 = time.perf_counter()
    r = fn()
    dt = time.perf_counter() - t0
    r.raise_for_status()
    return dt


def p95(xs):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, math.ceil(0.95 * len(xs)) - 1)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://localhost:8000")
    ap.add_argument("--repeats", type=int, default=4)
    ap.add_argument("--skip-business", action="store_true")
    a = ap.parse_args()

    calls = {
        "/site-eval": lambda lat, lng: requests.post(
            f"{a.base}/site-eval", json={"lat": lat, "lng": lng, "radius_m": 1500}, timeout=120),
        "/competitor-analysis": lambda lat, lng: requests.post(
            f"{a.base}/competitor-analysis",
            json={"lat": lat, "lng": lng, "business_type": "cafe", "radius_m": 1500}, timeout=120),
    }
    if not a.skip_business:
        calls["/business-estimate"] = lambda lat, lng: requests.post(
            f"{a.base}/business-estimate",
            json={"business_type": "cafe", "lat": lat, "lng": lng}, timeout=180)

    rows = []
    for name, call in calls.items():
        call(*POINTS[0][1:])  # warm-up, excluded
        xs = []
        for _ in range(a.repeats):
            for _, lat, lng in POINTS:
                xs.append(timed(lambda: call(lat, lng)))
        rows.append((name, len(xs), statistics.median(xs), p95(xs)))
        print(f"{name}: n={len(xs)} median={rows[-1][2]:.2f}s p95={rows[-1][3]:.2f}s")

    print("\n| endpoint | n | median s | p95 s |\n|---|---|---|---|")
    for name, n, med, hi in rows:
        print(f"| {name} | {n} | {med:.2f} | {hi:.2f} |")


if __name__ == "__main__":
    main()
