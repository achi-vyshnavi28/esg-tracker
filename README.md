# ESG Tracker: GHG inventory and sustainability reporting for a retail network

A complete quarterly ESG reporting cycle for a fashion retail network of **41 sites** (36 stores, 3 warehouses,
2 corporate offices): collect monthly site submissions, validate and reconcile them, calculate the **Scope 1, 2 and 3**
GHG inventory with official emission factors, track environmental KPIs against targets, and produce the **Excel
MIS workbook** and the **quarterly CXO presentation**.

```
site submissions (monthly)  +  utility bills  +  company freight and travel
        |
validate: completeness, duplicates, negatives, unit slips, impossible values
reconcile: electricity vs utility bill per site and quarter (2% tolerance)
estimate: remaining gaps from the site's own average, flagged
        |
GHG Protocol inventory (Scope 1, 2 location based, 3 categories 4 and 6)  +  KPIs vs targets
        |
out/esg_workbook.xlsx            live formulas, SUMIFS by quarter, charts, validation log, reconciliation
out/quarterly_performance.pptx   7 slides: targets, emissions by scope, trends, data quality, risks, method
```

The activity data is **simulated** and seeded (no company's real data is used). The emission factors, the GHG method,
the data checks and the reporting are real; see [docs/METHODOLOGY.md](docs/METHODOLOGY.md).

## Results, FY 2025-26

| | |
|---|---|
| Site months expected / submissions received | 492 / 489 |
| Data issues found and resolved | 17: 6 missing, 3 duplicate, 2 unit errors (MWh as kWh), 1 negative reading, 2 recycled above total, 3 bill variances |
| Scope 1 | 291 t CO2e (DG diesel, canteen LPG, refrigerant top ups) |
| Scope 2 (location based) | 8,108 t CO2e, 81% of the footprint |
| Scope 3 (freight, business air travel) | 1,668 t CO2e |
| Total | 10,067 t CO2e |
| Energy | 46,940 GJ |

| KPI | FY 2024-25 | FY 2025-26 | Target | Status |
|---|---|---|---|---|
| Scope 1 and 2 intensity, kg CO2e per sq ft | 15.41 | 14.86 (-3.6%) | -5% | Not met |
| Renewable electricity share | | 10.1% | 12% | Not met |
| Waste diversion | 68.3% | 67.9% | 65% | Met |
| Water intensity, kl per sq ft | 0.224 | 0.213 (-4.7%) | -3% | Met |

Three store quarters had under reported electricity (5 to 7% below the utility bill); they were aligned to the bill.
Every emission figure in the workbook is an Excel formula over the activity data and the factor table, checked to
match the Python calculation exactly when recalculated in Excel.

## Run

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pytest                 # 7 tests: every planted issue found, bills reconciled, factor maths, outputs built
python -m esg.run      # writes out/esg_workbook.xlsx, out/quarterly_performance.pptx, out/summary.json
```

## Frameworks

Outputs map to **SEBI BRSR Principle 6** essential indicators and **GRI 302, 303, 305 and 306**; see
[docs/framework_mapping.md](docs/framework_mapping.md).

## Layout

```
esg/factors.yaml   emission factors with sources (CEA, IPCC 2006, IPCC AR5, DEFRA 2024)
esg/simulate.py    seeded monthly submissions, utility bills, baseline year, planted data problems
esg/validate.py    completeness, validity, bill reconciliation, estimation, issue log
esg/calc.py        Scope 1, 2 and 3 inventory, energy, water, waste, KPIs vs targets
esg/excel.py       MIS workbook with live formulas and charts
esg/deck.py        quarterly CXO deck with native charts
docs/              methodology and framework mapping
```

MIT License.
