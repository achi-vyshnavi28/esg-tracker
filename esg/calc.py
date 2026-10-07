"""GHG inventory (Scope 1, 2 and 3) and environmental KPIs against targets, by quarter."""
from collections import defaultdict
from pathlib import Path

import yaml

from esg.simulate import MONTHS, quarter

FACTORS = yaml.safe_load((Path(__file__).parent / "factors.yaml").read_text(encoding="utf-8"))
QUARTERS = ["Q1", "Q2", "Q3", "Q4"]

# FY 2025-26 targets set against the FY 2024-25 baseline
TARGETS = {
    "scope12_intensity_reduction_pct": 5.0,   # kg CO2e per sq ft, versus last year
    "renewable_share_pct": 12.0,              # share of electricity from rooftop solar
    "waste_diversion_pct": 65.0,              # share of waste recycled rather than landfilled
    "water_intensity_reduction_pct": 3.0,     # kl per sq ft, versus last year
}


def f(scope, name):
    return FACTORS[scope][name]["value"]


def row_emissions(r):
    """Tonnes CO2e for one site month, split by source."""
    return {
        "scope1_diesel": r["diesel_litres"] * f("scope1", "diesel") / 1000,
        "scope1_lpg": r["lpg_kg"] * f("scope1", "lpg") / 1000,
        "scope1_refrigerant": r["refrigerant_kg"] * f("scope1", "r410a") / 1000,
        "scope2_grid": r["grid_kwh"] * f("scope2", "grid_electricity") / 1000,
    }


def company_emissions(c):
    return {"scope3_freight": c["freight_tonne_km"] * f("scope3", "freight") / 1000,
            "scope3_air": c["air_passenger_km"] * f("scope3", "air_travel") / 1000}


def totals(rows, company=None):
    out = defaultdict(float)
    for r in rows:
        for k, v in row_emissions(r).items():
            out[k] += v
        for k in ("grid_kwh", "solar_kwh", "diesel_litres", "lpg_kg", "water_kl", "waste_kg", "recycled_kg"):
            out[k] += r[k]
    for c in company or []:
        for k, v in company_emissions(c).items():
            out[k] += v
    out["scope1"] = out["scope1_diesel"] + out["scope1_lpg"] + out["scope1_refrigerant"]
    out["scope2"] = out["scope2_grid"]
    out["scope3"] = out["scope3_freight"] + out["scope3_air"]
    e = FACTORS["energy"]
    out["energy_gj"] = ((out["grid_kwh"] + out["solar_kwh"]) * e["kwh_to_mj"] + out["diesel_litres"] * e["diesel_mj_per_litre"]
                        + out["lpg_kg"] * e["lpg_mj_per_kg"]) / 1000
    elec = out["grid_kwh"] + out["solar_kwh"]
    out["renewable_share_pct"] = 100 * out["solar_kwh"] / elec if elec else 0.0
    out["waste_diversion_pct"] = 100 * out["recycled_kg"] / out["waste_kg"] if out["waste_kg"] else 0.0
    return dict(out)


def inventory(sites, clean, company, baseline):
    area = sum(s["area_sqft"] for s in sites)
    year = totals(clean, company)
    base = totals(baseline)
    by_q = {q: totals([r for r in clean if quarter(r["month"]) == q], [c for c in company if quarter(c["month"]) == q])
            for q in QUARTERS}
    by_type = {}
    kind = {s["site_id"]: s["type"] for s in sites}
    for t in ("store", "warehouse", "office"):
        by_type[t] = totals([r for r in clean if kind[r["site_id"]] == t])
    per_site = sorted(((r_site, totals([r for r in clean if r["site_id"] == r_site])["scope2"]
                        + totals([r for r in clean if r["site_id"] == r_site])["scope1"]) for r_site in kind),
                      key=lambda x: -x[1])

    i_now = (year["scope1"] + year["scope2"]) * 1000 / area
    i_base = (base["scope1"] + base["scope2"]) * 1000 / area
    w_now, w_base = year["water_kl"] / area, base["water_kl"] / area
    kpis = [
        {"kpi": "Scope 1 and 2 intensity, kg CO2e per sq ft", "baseline": i_base, "actual": i_now,
         "change_pct": 100 * (i_now - i_base) / i_base, "target": f"-{TARGETS['scope12_intensity_reduction_pct']:.0f}%",
         "met": 100 * (i_base - i_now) / i_base >= TARGETS["scope12_intensity_reduction_pct"]},
        {"kpi": "Renewable electricity share, %", "baseline": None, "actual": year["renewable_share_pct"],
         "change_pct": None, "target": f"{TARGETS['renewable_share_pct']:.0f}%",
         "met": year["renewable_share_pct"] >= TARGETS["renewable_share_pct"]},
        {"kpi": "Waste diversion, %", "baseline": base["waste_diversion_pct"], "actual": year["waste_diversion_pct"],
         "change_pct": None, "target": f"{TARGETS['waste_diversion_pct']:.0f}%",
         "met": year["waste_diversion_pct"] >= TARGETS["waste_diversion_pct"]},
        {"kpi": "Water intensity, kl per sq ft", "baseline": w_base, "actual": w_now,
         "change_pct": 100 * (w_now - w_base) / w_base, "target": f"-{TARGETS['water_intensity_reduction_pct']:.0f}%",
         "met": 100 * (w_base - w_now) / w_base >= TARGETS["water_intensity_reduction_pct"]},
    ]
    return {"year": year, "baseline": base, "by_quarter": by_q, "by_type": by_type, "top_sites": per_site[:5],
            "kpis": kpis, "area_sqft": area, "months": MONTHS}
