"""Simulated monthly ESG data submissions for a fashion retail network: 36 stores, 3 warehouses, 2 corporate offices.

The activity data is simulated and seeded (no company's real data is used); the emission factors, the GHG Protocol
method and the validation, reconciliation and reporting steps are real. Problems are planted on purpose, the way
they show up in real submissions, so the validation step has something to find:
  6 missing site months, 3 duplicate rows, 2 electricity readings entered in MWh instead of kWh,
  1 negative water reading, 2 rows where recycled waste exceeds total waste,
  3 site quarters where submitted electricity disagrees with the utility bill.
"""
import random

MONTHS = [f"2025-{m:02d}" for m in range(4, 13)] + [f"2026-{m:02d}" for m in range(1, 4)]   # FY 2025-26
SEASON = {4: 1.25, 5: 1.30, 6: 1.20, 7: 1.0, 8: 0.98, 9: 1.0, 10: 1.02, 11: 0.92, 12: 0.85, 1: 0.84, 2: 0.9, 3: 1.1}
CITIES = ["Mumbai", "Pune", "Bengaluru", "Hyderabad", "Chennai", "Delhi", "Gurugram", "Kolkata", "Ahmedabad", "Jaipur",
          "Lucknow", "Kochi"]
FIELDS = ["grid_kwh", "solar_kwh", "diesel_litres", "lpg_kg", "refrigerant_kg", "water_kl", "waste_kg", "recycled_kg"]


def sites(rng):
    out = []
    for i in range(1, 37):
        out.append({"site_id": f"ST{i:02d}", "type": "store", "city": CITIES[(i - 1) % len(CITIES)],
                    "area_sqft": rng.randrange(3000, 12001, 250)})
    for i in range(1, 4):
        out.append({"site_id": f"WH{i}", "type": "warehouse", "city": ["Bhiwandi", "Bengaluru", "Gurugram"][i - 1],
                    "area_sqft": rng.randrange(60000, 90001, 1000)})
    for i in range(1, 3):
        out.append({"site_id": f"CO{i}", "type": "office", "city": ["Mumbai", "Bengaluru"][i - 1],
                    "area_sqft": rng.randrange(35000, 45001, 500)})
    return out


def _month_row(rng, site, month, scale=1.0):
    s, f = site, SEASON[int(month[5:])]
    a = s["area_sqft"]
    if s["type"] == "store":
        grid, solar = a * rng.uniform(2.0, 2.4) * f, 0.0
        diesel, lpg = rng.uniform(15, 140), 0.0
        water, waste = a * rng.uniform(0.018, 0.024), rng.uniform(300, 900)
        recycled = waste * rng.uniform(0.5, 0.68)
    elif s["type"] == "warehouse":
        use = a * rng.uniform(1.1, 1.3) * f
        solar = use * rng.uniform(0.3, 0.38) * (1.15 if f > 1.1 else 0.9 if f < 0.9 else 1.0)
        grid, diesel, lpg = use - solar, rng.uniform(250, 600), 0.0
        water, waste = a * rng.uniform(0.006, 0.008), rng.uniform(9000, 14000)
        recycled = waste * rng.uniform(0.72, 0.8)
    else:
        use = a * rng.uniform(1.6, 1.9) * f
        solar = use * rng.uniform(0.08, 0.12)
        grid, diesel, lpg = use - solar, rng.uniform(40, 120), rng.uniform(300, 500)
        water, waste = a * rng.uniform(0.03, 0.036), rng.uniform(1500, 2500)
        recycled = waste * rng.uniform(0.45, 0.6)
    refrigerant = rng.choice([2.0, 3.5, 5.0]) if rng.random() < 0.05 else 0.0
    vals = [grid * scale, solar, diesel * scale, lpg * scale, refrigerant, water * scale, waste * scale, recycled * scale]
    return {"site_id": s["site_id"], "month": month, **{k: round(v, 1) for k, v in zip(FIELDS, vals)}}


def generate(seed=11):
    """Return (sites, submissions, bills, company_rows, baseline) for FY 2025-26 plus the FY 2024-25 baseline."""
    rng = random.Random(seed)
    site_list = sites(rng)
    truth = [_month_row(rng, s, m) for s in site_list for m in MONTHS]
    baseline = [_month_row(rng, s, m, scale=1.045) for s in site_list for m in MONTHS]   # last year ran ~4.5% hotter

    # utility bills per site and quarter are built from the true readings, before any submission error
    bills = {}
    for r in truth:
        q = quarter(r["month"])
        bills[(r["site_id"], q)] = bills.get((r["site_id"], q), 0.0) + r["grid_kwh"]
    bills = [{"site_id": k[0], "quarter": k[1], "billed_kwh": round(v, 1)} for k, v in sorted(bills.items())]

    subs = [dict(r) for r in truth]
    order = list(range(len(subs)))
    rng.shuffle(order)
    picks = iter(order)
    nxt = lambda: subs[next(picks)]                                   # noqa: E731
    missing = {id(nxt()) for _ in range(6)}
    dup = [dict(nxt()) for _ in range(3)]
    for _ in range(2):
        r = nxt(); r["grid_kwh"] = round(r["grid_kwh"] / 1000, 3)       # entered in MWh
    r = nxt(); r["water_kl"] = -abs(r["water_kl"])
    for _ in range(2):
        r = nxt(); r["recycled_kg"] = round(r["waste_kg"] * 1.3, 1)
    under = []
    while len(under) < 3:                                              # under reported electricity, caught by bills
        r = nxt()
        if r["site_id"].startswith("ST") and id(r) not in missing and r["grid_kwh"] > 1000:
            r["grid_kwh"] = round(r["grid_kwh"] * 0.82, 1)
            under.append((r["site_id"], quarter(r["month"])))
    subs = [r for r in subs if id(r) not in missing] + dup
    rng.shuffle(subs)

    company = [{"month": m, "freight_tonne_km": round(rng.uniform(0.9e6, 1.2e6) * SEASON[int(m[5:])]),
                "air_passenger_km": round(rng.uniform(150e3, 250e3))} for m in MONTHS]
    return site_list, subs, bills, company, baseline


def quarter(month):
    y, m = int(month[:4]), int(month[5:])
    fy_q = {4: 1, 5: 1, 6: 1, 7: 2, 8: 2, 9: 2, 10: 3, 11: 3, 12: 3, 1: 4, 2: 4, 3: 4}[m]
    return f"Q{fy_q}"
