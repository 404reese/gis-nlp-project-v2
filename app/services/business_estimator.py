"""Location-aware business setup cost estimator.

Grounds the location-dependent cost (rent + deposit) in REAL nearby property data, then
uses the LLM to fill business-type-specific line items (interior, furniture, equipment,
stock, staff, utilities incl. gas, licenses...). Everything is clearly split into one-time
(capex) and monthly (opex), with a working-capital buffer. Amounts in INR (Mumbai).

This mirrors the project thesis: real data where we have it, modeled where we don't — and
we say which is which (see `rent_basis`).
"""
from __future__ import annotations

import asyncio
import json

from sqlalchemy import text

from app.db_spatial import get_engine
from app.services.groq_client import call_groq, parse_json_safely

CR = 1e7  # 1 crore
L = 1e5   # 1 lakh

# Typical footprint (sqft) by business type; fallback 800.
DEFAULT_SIZE = {
    "cafe": 800, "coffee shop": 800, "restaurant": 1500, "cloud kitchen": 500,
    "bakery": 600, "bar": 1200, "retail store": 600, "clothing store": 700,
    "boutique": 600, "salon": 500, "spa": 900, "gym": 2500, "clinic": 700,
    "pharmacy": 300, "grocery store": 700, "supermarket": 2000, "bookstore": 700,
}

DEPOSIT_MONTHS = 6          # commercial security deposit (Mumbai norm ~6-12)
COMMERCIAL_RENT_PREMIUM = 1.15
SALE_TO_MONTHLY_RENT = 0.005  # monthly rent ~ 0.5% of capital value per sqft
WORKING_CAPITAL_MONTHS = 3


async def _local_psf(lat: float, lng: float, city_id: int, radius_m: int = 2500):
    """Median sale price per sqft from listings near the point (real data)."""
    engine = get_engine()
    sql = text(
        """
        SELECT price, price_unit, area_sqft
        FROM realestate.listing
        WHERE city_id = :c AND area_sqft > 100 AND price > 0
          AND ST_DWithin(geom::geography,
                         ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography, :r)
        """
    )
    async with engine.connect() as conn:
        rows = (await conn.execute(sql, {"c": city_id, "lng": lng, "lat": lat, "r": radius_m})).fetchall()
    psf = []
    for price, unit, area in rows:
        mult = CR if (unit or "").strip().lower().startswith("cr") else L
        if area and area > 0:
            psf.append(price * mult / area)
    if not psf:
        return None, 0
    psf.sort()
    return psf[len(psf) // 2], len(psf)


# --- Revenue model -------------------------------------------------------------------
# Benchmarks per business type: (poi categories that count as competitors, average ticket ₹,
# base customers/day per 100 sqft at a "typical" location, cost of goods as share of revenue).
# These are modeled assumptions (not measured) and are surfaced as such in the response.
REV_BENCH = {
    "cafe":          (["cafe"], 300, 18, 0.30),
    "coffee shop":   (["cafe"], 300, 18, 0.30),
    "restaurant":    (["restaurant", "fast_food"], 650, 9, 0.33),
    "cloud kitchen": (["restaurant", "fast_food"], 450, 25, 0.35),
    "bakery":        (["cafe", "bakery"], 250, 20, 0.40),
    "bar":           (["bar", "pub"], 1100, 6, 0.30),
    "pharmacy":      (["pharmacy"], 450, 30, 0.72),
    "clinic":        (["clinic", "doctors", "hospital"], 700, 5, 0.10),
    "grocery store": (["supermarket", "convenience", "marketplace"], 400, 22, 0.78),
    "supermarket":   (["supermarket", "mall"], 900, 8, 0.80),
    "retail store":  (["shop", "mall"], 1500, 4, 0.55),
    "clothing store": (["shop", "mall"], 2000, 3, 0.55),
    "boutique":      (["shop"], 3000, 2, 0.50),
    "salon":         (["salon", "beauty"], 800, 6, 0.20),
    "spa":           (["spa", "salon"], 2500, 2, 0.20),
    "gym":           (["gym", "fitness_centre"], 1800, 1.5, 0.05),
    "bookstore":     (["books", "bookstore"], 500, 6, 0.65),
}
GENERIC_BENCH = ([], 500, 8, 0.45)
TIER_TICKET = {"economy": 0.8, "standard": 1.0, "premium": 1.3}
SCENARIOS = [("Conservative", 0.7), ("Base", 1.0), ("Optimistic", 1.3)]


async def _catchment(lat: float, lng: float, city_id: int, categories: list[str]) -> dict:
    """Footfall proxies (amenity density, transit) + same-category competitor count."""
    from app.services.site_evaluator import _amenities, _transit

    engine = get_engine()
    async with engine.connect() as conn:
        amenities = await _amenities(conn, lat, lng, city_id, 1000)
        transit = await _transit(conn, lat, lng, city_id, 800)
        competitors = None
        if categories:
            competitors = (await conn.execute(text(
                """
                SELECT COUNT(*) FROM poi.place
                WHERE city_id = :c AND lower(category) = ANY(:cats)
                  AND ST_DWithin(geom::geography,
                                 ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography, 1000)
                """
            ), {"c": city_id, "cats": categories, "lng": lng, "lat": lat})).scalar()
    return {"amenities": amenities, "transit": transit, "competitors": competitors}


def _revenue_model(business_type: str, size: int, tier: str, catch: dict,
                   monthly_total: int, restock: int, one_time_total: int) -> dict:
    cats, ticket, per100, cogs_pct = REV_BENCH.get(business_type.strip().lower(), GENERIC_BENCH)
    ticket = ticket * TIER_TICKET.get(tier, 1.0)

    amen_total = sum(catch["amenities"].values())
    near_transit = any(t["distance_m"] <= 800 and t["mode"] in ("metro", "rail") for t in catch["transit"])
    # Footfall: 0.6x in a quiet pocket up to 1.5x in a dense, transit-served one.
    footfall = 0.6 + 0.8 * min(1.0, amen_total / 120) + (0.1 if near_transit else 0.0)
    comp = catch["competitors"]
    comp_mult = 1.0 if comp is None else max(0.6, 1 / (1 + 0.04 * comp))

    daily = size / 100 * per100 * footfall * comp_mult
    fixed = monthly_total - restock  # restock is replaced by COGS % of revenue below

    def scenario(name: str, mult: float) -> dict:
        rev = daily * mult * ticket * 30
        profit = rev - rev * cogs_pct - fixed
        return {
            "name": name,
            "daily_customers": round(daily * mult),
            "monthly_revenue": round(rev),
            "monthly_profit": round(profit),
            "payback_months": round(one_time_total / profit, 1) if profit > 0 else None,
        }

    base_margin = 1 - cogs_pct
    return {
        "avg_ticket": round(ticket),
        "cogs_pct": cogs_pct,
        "fixed_costs": fixed,
        "breakeven_revenue": round(fixed / base_margin) if base_margin > 0 else None,
        "breakeven_daily_customers": round(fixed / base_margin / (ticket * 30)) if base_margin > 0 else None,
        "scenarios": [scenario(n, m) for n, m in SCENARIOS],
        "drivers": {
            "footfall_multiplier": round(footfall, 2),
            "competition_multiplier": round(comp_mult, 2),
            "competitors_1km": comp,
            "amenities_1km": amen_total,
            "near_metro_or_rail": near_transit,
        },
        "note": (
            f"Modeled, not measured: {size} sqft × benchmark footfall for a {business_type} × location "
            f"multiplier ({footfall:.2f}× from {amen_total} amenities within 1 km"
            f"{', metro/rail within 800 m' if near_transit else ''}) × competition factor "
            f"({comp_mult:.2f}× from {comp if comp is not None else 'n/a'} competitors within 1 km). "
            f"Average ticket ₹{ticket:,.0f}; cost of goods {cogs_pct:.0%} of revenue replaces the fixed "
            "restock line. Payback = one-time setup ÷ monthly profit."
        ),
    }


async def _llm_line_items(business_type: str, city: str, size: int, tier: str, monthly_rent: int) -> dict:
    prompt = f"""You are a small-business setup cost estimator for {city} (India). Give a
realistic cost breakdown in INR for opening a {business_type} of about {size} sqft, {tier} tier.

The monthly rent is already fixed at ₹{monthly_rent:,} — do NOT include rent or security
deposit; those are handled separately. Estimate everything else with realistic Mumbai numbers.

Return STRICT JSON, integers in rupees:
{{
  "capex": {{
    "interior_fitout": int, "furniture_fixtures": int, "equipment": int,
    "initial_inventory": int, "licenses_registration": int, "branding_setup": int
  }},
  "opex_monthly": {{
    "electricity": int, "gas": int, "water": int, "internet_phone": int,
    "inventory_restock": int, "marketing": int, "misc": int
  }},
  "staff": [{{"role": "string", "count": int, "monthly_salary": int}}],
  "assumptions": ["short bullet strings"],
  "summary": "2-3 sentence overview of the opportunity and cost profile at this location"
}}"""
    raw = await asyncio.to_thread(call_groq, prompt)
    return parse_json_safely(raw)


def _fallback_line_items(size: int) -> dict:
    """Heuristic used if the LLM is unavailable, so the tool never hard-fails."""
    return {
        "capex": {
            "interior_fitout": size * 1800, "furniture_fixtures": size * 500,
            "equipment": 600000, "initial_inventory": 300000,
            "licenses_registration": 75000, "branding_setup": 120000,
        },
        "opex_monthly": {
            "electricity": 25000, "gas": 8000, "water": 3000, "internet_phone": 4000,
            "inventory_restock": 150000, "marketing": 30000, "misc": 20000,
        },
        "staff": [{"role": "Staff", "count": 4, "monthly_salary": 20000}],
        "assumptions": ["Modeled from size only (LLM unavailable)."],
        "summary": "Estimated from floor area and typical Mumbai cost norms.",
    }


async def estimate_business(business_type: str, lat: float, lng: float, city_id: int = 1,
                            size_sqft: int | None = None, tier: str = "standard") -> dict:
    size = int(size_sqft or DEFAULT_SIZE.get(business_type.strip().lower(), 800))

    # 1. Location-grounded rent + deposit
    psf, n = await _local_psf(lat, lng, city_id)
    if psf:
        rent_psf_month = psf * SALE_TO_MONTHLY_RENT * COMMERCIAL_RENT_PREMIUM
        rent_basis = (
            f"estimated ₹{rent_psf_month:,.1f}/sqft/month (₹{rent_psf_month * 12:,.0f}/sqft/year) × {size} sqft. "
            f"Derived, not a listed rent: median sale value of {n} nearby listings "
            f"(₹{psf:,.0f}/sqft) × {SALE_TO_MONTHLY_RENT:.1%} monthly yield × "
            f"{COMMERCIAL_RENT_PREMIUM:.2f} commercial premium"
        )
        measured = True
    else:
        rent_psf_month = 120.0
        rent_basis = (
            f"no nearby listings found — city default ₹{rent_psf_month:,.0f}/sqft/month × {size} sqft"
        )
        measured = False
    monthly_rent = int(round(rent_psf_month * size))
    deposit = monthly_rent * DEPOSIT_MONTHS

    # 2. LLM (or fallback) for everything else
    try:
        li = await _llm_line_items(business_type, "Mumbai", size, tier, monthly_rent)
        capex = li.get("capex", {})
        opex = li.get("opex_monthly", {})
        staff = li.get("staff", []) or []
        assumptions = li.get("assumptions", [])
        summary = li.get("summary", "")
    except Exception:  # noqa: BLE001
        li = _fallback_line_items(size)
        capex, opex, staff = li["capex"], li["opex_monthly"], li["staff"]
        assumptions, summary = li["assumptions"], li["summary"]

    def _i(v):
        try:
            return max(0, int(v))
        except (TypeError, ValueError):
            return 0

    # 3. Assemble
    one_time = [{"item": "Security deposit", "amount": deposit,
                 "note": f"{DEPOSIT_MONTHS} months rent"}]
    for key, label in [
        ("interior_fitout", "Interior & fit-out"), ("furniture_fixtures", "Furniture & fixtures"),
        ("equipment", "Equipment"), ("initial_inventory", "Initial inventory / stock"),
        ("licenses_registration", "Licenses & registration"), ("branding_setup", "Branding & setup"),
    ]:
        one_time.append({"item": label, "amount": _i(capex.get(key)), "note": ""})

    staff_total = sum(_i(s.get("count")) * _i(s.get("monthly_salary")) for s in staff)
    staff_desc = ", ".join(f"{_i(s.get('count'))}× {s.get('role', 'staff')}" for s in staff) or "team"
    monthly = [
        {"item": "Rent", "amount": monthly_rent, "note": rent_basis},
        {"item": "Staff salaries", "amount": staff_total, "note": staff_desc},
    ]
    for key, label in [
        ("electricity", "Electricity"), ("gas", "Gas"), ("water", "Water"),
        ("internet_phone", "Internet & phone"), ("inventory_restock", "Inventory restock (COGS)"),
        ("marketing", "Marketing"), ("misc", "Miscellaneous"),
    ]:
        monthly.append({"item": label, "amount": _i(opex.get(key)), "note": ""})

    one_time_total = sum(x["amount"] for x in one_time)
    monthly_total = sum(x["amount"] for x in monthly)
    working_capital = monthly_total * WORKING_CAPITAL_MONTHS
    startup_total = one_time_total + working_capital

    try:
        cats = REV_BENCH.get(business_type.strip().lower(), GENERIC_BENCH)[0]
        catch = await _catchment(lat, lng, city_id, cats)
        restock = _i(opex.get("inventory_restock"))
        revenue = _revenue_model(business_type, size, tier, catch, monthly_total, restock, one_time_total)
    except Exception:  # noqa: BLE001  - revenue is additive; never fail the cost estimate
        revenue = None

    return {
        "revenue": revenue,
        "business_type": business_type,
        "location": {"lat": lat, "lng": lng},
        "size_sqft": size,
        "tier": tier,
        "rent_measured": measured,
        "rent_basis": rent_basis,
        "staff": [{"role": s.get("role"), "count": _i(s.get("count")),
                   "monthly_salary": _i(s.get("monthly_salary"))} for s in staff],
        "one_time": one_time,
        "monthly": monthly,
        "totals": {
            "one_time": one_time_total,
            "monthly": monthly_total,
            "working_capital": working_capital,
            "working_capital_months": WORKING_CAPITAL_MONTHS,
            "startup_total": startup_total,
        },
        "assumptions": assumptions,
        "summary": summary,
        "disclaimer": "Indicative estimate for planning only; not financial advice. "
                      "Rent is estimated from nearby sale prices (no rental listings in the dataset); "
                      "other line items are modeled.",
    }
