"""The ESG data workbook: every emission figure is a live Excel formula over the activity data and the factor table,
so a reviewer can trace and recompute any number. Charts are native Excel charts."""
from openpyxl import Workbook
from openpyxl.chart import BarChart, LineChart, Reference
from openpyxl.formatting.rule import CellIsRule
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from esg.calc import FACTORS, QUARTERS
from esg.simulate import quarter

HEAD = Font(bold=True, color="FFFFFF")
FILL = PatternFill("solid", fgColor="2F5D50")
GREEN = PatternFill("solid", fgColor="C6EFCE")
RED = PatternFill("solid", fgColor="FFC7CE")

FACTOR_ROWS = [("scope1", "diesel"), ("scope1", "lpg"), ("scope1", "r410a"), ("scope2", "grid_electricity"),
               ("scope3", "freight"), ("scope3", "air_travel")]
FCELL = {name: f"Factors!$C${i + 2}" for i, (_, name) in enumerate(FACTOR_ROWS)}


def _header(ws, cols):
    ws.append(cols)
    for c in ws[1]:
        c.font, c.fill, c.alignment = HEAD, FILL, Alignment(wrap_text=True, vertical="center")
    ws.freeze_panes = "A2"
    for i, name in enumerate(cols, 1):
        ws.column_dimensions[get_column_letter(i)].width = max(12, min(40, len(name) + 4))


def build(path, sites, clean, company, issues, recon, inv):
    wb = Workbook()
    kind = {s["site_id"]: s for s in sites}

    # Factors
    ws = wb.active
    ws.title = "Factors"
    _header(ws, ["Scope", "Factor", "Value", "Unit", "Source"])
    for scope, name in FACTOR_ROWS:
        x = FACTORS[scope][name]
        ws.append([scope, name, x["value"], x["unit"], x["source"]])
    ws.column_dimensions["E"].width = 90

    # Activity: one row per site month, emissions as formulas
    wa = wb.create_sheet("Activity")
    cols = ["Site", "Type", "City", "Area sq ft", "Quarter", "Month", "Grid kWh", "Solar kWh", "Diesel L", "LPG kg",
            "Refrigerant kg", "Water kl", "Waste kg", "Recycled kg", "Estimated fields", "Scope 1 tCO2e", "Scope 2 tCO2e"]
    _header(wa, cols)
    for i, r in enumerate(clean, start=2):
        s = kind[r["site_id"]]
        wa.append([r["site_id"], s["type"], s["city"], s["area_sqft"], quarter(r["month"]), r["month"], r["grid_kwh"],
                   r["solar_kwh"], r["diesel_litres"], r["lpg_kg"], r["refrigerant_kg"], r["water_kl"], r["waste_kg"],
                   r["recycled_kg"], ", ".join(r["estimated"]),
                   f"=(I{i}*{FCELL['diesel']}+J{i}*{FCELL['lpg']}+K{i}*{FCELL['r410a']})/1000",
                   f"=G{i}*{FCELL['grid_electricity']}/1000"])
    n = len(clean) + 1
    wa.auto_filter.ref = f"A1:Q{n}"

    # Company level Scope 3
    wc = wb.create_sheet("Scope 3")
    _header(wc, ["Quarter", "Month", "Freight tonne km", "Air passenger km", "Freight tCO2e", "Air travel tCO2e"])
    for i, c in enumerate(company, start=2):
        wc.append([quarter(c["month"]), c["month"], c["freight_tonne_km"], c["air_passenger_km"],
                   f"=C{i}*{FCELL['freight']}/1000", f"=D{i}*{FCELL['air_travel']}/1000"])
    m = len(company) + 1

    # By quarter: SUMIFS over the activity sheet
    wq = wb.create_sheet("By Quarter")
    _header(wq, ["Quarter", "Scope 1 tCO2e", "Scope 2 tCO2e", "Scope 3 tCO2e", "Total tCO2e", "Grid kWh", "Solar kWh",
                 "Renewable share %", "Waste kg", "Recycled kg", "Waste diversion %", "Water kl"])
    rng = lambda col: f"Activity!${col}$2:${col}${n}"                     # noqa: E731
    for i, q in enumerate(QUARTERS, start=2):
        crit = f'Activity!$E$2:$E${n},"{q}"'
        wq.append([q, f"=SUMIFS({rng('P')},{crit})", f"=SUMIFS({rng('Q')},{crit})",
                   f'=SUMIFS(\'Scope 3\'!$E$2:$E${m},\'Scope 3\'!$A$2:$A${m},"{q}")'
                   f'+SUMIFS(\'Scope 3\'!$F$2:$F${m},\'Scope 3\'!$A$2:$A${m},"{q}")',
                   f"=B{i}+C{i}+D{i}", f"=SUMIFS({rng('G')},{crit})", f"=SUMIFS({rng('H')},{crit})",
                   f"=100*G{i}/(F{i}+G{i})", f"=SUMIFS({rng('M')},{crit})", f"=SUMIFS({rng('N')},{crit})",
                   f"=100*J{i}/I{i}", f"=SUMIFS({rng('L')},{crit})"])
    wq.append(["FY 2025-26", "=SUM(B2:B5)", "=SUM(C2:C5)", "=SUM(D2:D5)", "=SUM(E2:E5)", "=SUM(F2:F5)",
               "=SUM(G2:G5)", "=100*G6/(F6+G6)", "=SUM(I2:I5)", "=SUM(J2:J5)", "=100*J6/I6", "=SUM(L2:L5)"])
    for row in wq.iter_rows(min_row=2, max_row=6, min_col=2, max_col=12):
        for c in row:
            c.number_format = "#,##0.0"
    stacked = BarChart()
    stacked.type, stacked.grouping, stacked.overlap = "col", "stacked", 100
    stacked.title, stacked.y_axis.title = "GHG emissions by scope and quarter", "tCO2e"
    stacked.add_data(Reference(wq, min_col=2, max_col=4, min_row=1, max_row=5), titles_from_data=True)
    stacked.set_categories(Reference(wq, min_col=1, min_row=2, max_row=5))
    stacked.width, stacked.height = 18, 9
    wq.add_chart(stacked, "A9")
    line = LineChart()
    line.title, line.y_axis.title = "Renewable share and waste diversion by quarter", "%"
    line.add_data(Reference(wq, min_col=8, min_row=1, max_row=5), titles_from_data=True)
    line.add_data(Reference(wq, min_col=11, min_row=1, max_row=5), titles_from_data=True)
    line.set_categories(Reference(wq, min_col=1, min_row=2, max_row=5))
    line.width, line.height = 18, 9
    wq.add_chart(line, "J9")

    # KPIs against targets
    wk = wb.create_sheet("KPIs vs Targets", 0)
    _header(wk, ["KPI", "FY 2024-25 baseline", "FY 2025-26 actual", "Change %", "Target", "Status"])
    for k in inv["kpis"]:
        wk.append([k["kpi"], None if k["baseline"] is None else round(k["baseline"], 3), round(k["actual"], 3),
                   None if k["change_pct"] is None else round(k["change_pct"], 1), k["target"],
                   "Met" if k["met"] else "Not met"])
    wk.column_dimensions["A"].width = 46
    wk.conditional_formatting.add("F2:F5", CellIsRule(operator="equal", formula=['"Met"'], fill=GREEN))
    wk.conditional_formatting.add("F2:F5", CellIsRule(operator="equal", formula=['"Not met"'], fill=RED))

    # Validation log and reconciliation
    wv = wb.create_sheet("Validation Log")
    _header(wv, ["Stage", "Check", "Site", "Period", "Detail", "Action"])
    for x in issues:
        wv.append([x.stage, x.check, x.site_id, x.period, x.detail, x.action])
    wv.column_dimensions["E"].width = wv.column_dimensions["F"].width = 50
    wr = wb.create_sheet("Reconciliation")
    _header(wr, ["Site", "Quarter", "Submitted kWh", "Billed kWh", "Variance %", "Status"])
    for x in recon:
        wr.append([x["site_id"], x["quarter"], x["submitted_kwh"], x["billed_kwh"], x["variance_pct"], x["status"]])
    wr.conditional_formatting.add(f"F2:F{len(recon) + 1}", CellIsRule(operator="equal", formula=['"adjusted to bill"'], fill=RED))
    wb.save(path)
    return path
