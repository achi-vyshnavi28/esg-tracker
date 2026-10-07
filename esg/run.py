"""Run the whole reporting cycle: collect -> validate -> reconcile -> calculate -> workbook, deck and summary.

    python -m esg.run          writes out/esg_workbook.xlsx, out/quarterly_performance.pptx, out/summary.json
"""
import dataclasses
import json
from pathlib import Path

from esg import calc, deck, excel, simulate, validate

OUT = Path(__file__).resolve().parents[1] / "out"


def run(out=OUT):
    out.mkdir(parents=True, exist_ok=True)
    sites, subs, bills, company, baseline = simulate.generate()
    clean, issues, recon = validate.validate(sites, subs, bills)
    inv = calc.inventory(sites, clean, company, baseline)
    excel.build(out / "esg_workbook.xlsx", sites, clean, company, issues, recon, inv)
    expected = len(sites) * len(simulate.MONTHS)
    deck.build(out / "quarterly_performance.pptx", inv, issues, recon, len(subs), expected)
    y = inv["year"]
    summary = {
        "sites": len(sites), "site_months_expected": expected, "submissions": len(subs),
        "issues": [dataclasses.asdict(i) for i in issues],
        "bill_adjustments": sum(r["status"] != "matched" for r in recon),
        "tco2e": {k: round(y[k], 1) for k in ("scope1", "scope2", "scope3")},
        "energy_gj": round(y["energy_gj"], 1),
        "renewable_share_pct": round(y["renewable_share_pct"], 1),
        "waste_diversion_pct": round(y["waste_diversion_pct"], 1),
        "water_kl": round(y["water_kl"], 1),
        "kpis": inv["kpis"],
        "by_quarter_total_tco2e": {q: round(v["scope1"] + v["scope2"] + v["scope3"], 1) for q, v in inv["by_quarter"].items()},
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


if __name__ == "__main__":
    s = run()
    print(f"{s['submissions']} submissions for {s['site_months_expected']} site months, {len(s['issues'])} issues logged")
    print(f"Scope 1 {s['tco2e']['scope1']:,} t, Scope 2 {s['tco2e']['scope2']:,} t, Scope 3 {s['tco2e']['scope3']:,} t CO2e")
    for k in s["kpis"]:
        print(f"  {k['kpi']}: {k['actual']:.2f} vs target {k['target']} -> {'met' if k['met'] else 'not met'}")
    print("wrote out/esg_workbook.xlsx, out/quarterly_performance.pptx, out/summary.json")
