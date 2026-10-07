"""Validation, reconciliation and gap filling for monthly site submissions.

Order matters and mirrors how an ESG team works a reporting cycle:
  1. completeness   every site submits every month; duplicates removed
  2. validity       negatives rejected, impossible combinations rejected, unit slips corrected
  3. reconciliation submitted electricity agrees with the utility bill per site and quarter (bill is the source of
                    truth); a missing month is filled from the bill
  4. estimation     any value still missing is estimated from the site's own average, and flagged as estimated
Every action is written to the issue log, so each reported number can be traced back.
"""
from collections import defaultdict
from dataclasses import dataclass
from statistics import median

from esg.simulate import FIELDS, MONTHS, quarter

BILL_TOLERANCE = 0.02


@dataclass
class Issue:
    stage: str
    check: str
    site_id: str
    period: str
    detail: str
    action: str


def validate(sites, submissions, bills):
    issues = []
    site_ids = [s["site_id"] for s in sites]

    # 1. completeness and duplicates
    rows, seen = {}, set()
    for r in submissions:
        key = (r["site_id"], r["month"])
        if key in seen:
            issues.append(Issue("completeness", "duplicate_submission", *key, "same site and month submitted twice",
                                "kept the first submission"))
            continue
        seen.add(key)
        rows[key] = {**r, "estimated": []}
    for s in site_ids:
        for m in MONTHS:
            if (s, m) not in rows:
                issues.append(Issue("completeness", "missing_submission", s, m, "no submission received",
                                    "filled from bill and site average"))
                rows[(s, m)] = {"site_id": s, "month": m, **{f: None for f in FIELDS}, "estimated": list(FIELDS)}

    # 2. validity
    by_site = defaultdict(list)
    for (s, _), r in rows.items():
        if r["grid_kwh"] is not None:
            by_site[s].append(r["grid_kwh"])
    for key, r in rows.items():
        for f in FIELDS:
            if r[f] is not None and r[f] < 0:
                issues.append(Issue("validity", "negative_value", *key, f"{f} = {r[f]}", "rejected and estimated"))
                r[f] = None
                r["estimated"].append(f)
        g = r["grid_kwh"]
        if g is not None and g > 0 and g < 0.02 * median(by_site[key[0]]):
            issues.append(Issue("validity", "unit_error", *key, f"grid_kwh = {g}, about 1/1000 of the site's usual month",
                                "entered in MWh, converted to kWh"))
            r["grid_kwh"] = round(g * 1000, 1)
        if r["waste_kg"] is not None and r["recycled_kg"] is not None and r["recycled_kg"] > r["waste_kg"]:
            issues.append(Issue("validity", "recycled_exceeds_total", *key,
                                f"recycled {r['recycled_kg']} kg > total {r['waste_kg']} kg", "recycled rejected and estimated"))
            r["recycled_kg"] = None
            r["estimated"].append("recycled_kg")

    # 3. reconciliation with utility bills
    bill = {(b["site_id"], b["quarter"]): b["billed_kwh"] for b in bills}
    recon = []
    for (s, q), billed in sorted(bill.items()):
        months = [m for m in MONTHS if quarter(m) == q]
        known = [rows[(s, m)] for m in months if rows[(s, m)]["grid_kwh"] is not None]
        gaps = [rows[(s, m)] for m in months if rows[(s, m)]["grid_kwh"] is None]
        if gaps:
            share = (billed - sum(r["grid_kwh"] for r in known)) / len(gaps)
            for r in gaps:
                r["grid_kwh"] = round(share, 1)
        submitted = sum(rows[(s, m)]["grid_kwh"] for m in months)
        variance = (submitted - billed) / billed
        status = "matched"
        if abs(variance) > BILL_TOLERANCE:
            status = "adjusted to bill"
            issues.append(Issue("reconciliation", "bill_variance", s, q, f"submitted {submitted:,.0f} kWh vs billed "
                                f"{billed:,.0f} kWh ({variance:+.1%})", "aligned to the utility bill"))
            for m in months:
                r = rows[(s, m)]
                r["grid_kwh"] = round(r["grid_kwh"] * billed / submitted, 1)
                if "grid_kwh" not in r["estimated"]:
                    r["estimated"].append("grid_kwh")
        recon.append({"site_id": s, "quarter": q, "submitted_kwh": round(submitted, 1), "billed_kwh": billed,
                      "variance_pct": round(100 * variance, 2), "status": status})

    # 4. estimation from the site's own average
    for s in site_ids:
        site_rows = [rows[(s, m)] for m in MONTHS]
        for f in FIELDS:
            vals = [r[f] for r in site_rows if r[f] is not None]
            avg = sum(vals) / len(vals) if vals else 0.0
            for r in site_rows:
                if r[f] is None:
                    if f == "recycled_kg" and r["waste_kg"]:
                        ratios = [x["recycled_kg"] / x["waste_kg"] for x in site_rows
                                  if x["recycled_kg"] is not None and x["waste_kg"]]
                        r[f] = round(r["waste_kg"] * sum(ratios) / len(ratios), 1)
                    else:
                        r[f] = round(avg, 1)
    clean = [rows[(s, m)] for s in site_ids for m in MONTHS]
    return clean, issues, recon
