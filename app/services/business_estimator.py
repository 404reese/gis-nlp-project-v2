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
        rent_basis = f"grounded in {n} nearby listings (median ≈ ₹{psf:,.0f}/sqft sale value)"
        measured = True
    else:
        rent_psf_month = 120.0
        rent_basis = "no nearby listings found — used a city default (₹120/sqft/mo)"
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

    return {
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
                      "Location-dependent rent is data-grounded; other line items are modeled.",
    }
