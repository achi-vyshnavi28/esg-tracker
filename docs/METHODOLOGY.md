# Methodology

## Boundary and standard
* **Standard:** GHG Protocol Corporate Accounting and Reporting Standard.
* **Boundary:** operational control. 41 sites: 36 retail stores, 3 warehouses, 2 corporate offices.
* **Period:** FY 2025-26 (April 2025 to March 2026), reported by fiscal quarter, against an FY 2024-25 baseline.
* **Data:** the activity data is **simulated** for a retail network and seeded, so every number is reproducible.
  No company's real data is used. Factors, method, checks and reporting are real.

## Scopes and factors (see `esg/factors.yaml`)

| Scope | Source | Activity data | Factor | Reference |
|---|---|---|---|---|
| 1 | DG set diesel | litres | 2.651 kg CO2 / L | IPCC 2006 defaults (NCV 43.0 TJ/Gg, 74,100 kg CO2/TJ, 0.832 kg/L) |
| 1 | Canteen LPG | kg | 2.985 kg CO2 / kg | IPCC 2006 defaults (NCV 47.3 TJ/Gg, 63,100 kg CO2/TJ) |
| 1 | Refrigerant R-410A top ups (fugitive) | kg | GWP 1,924 | IPCC AR5 GWP100 |
| 2 | Grid electricity (location based) | kWh | 0.727 kg CO2 / kWh | CEA CO2 Baseline Database Version 20.0, FY 2023-24 |
| 2 | Rooftop solar | kWh | 0 | on site renewable |
| 3, category 4 | Upstream road freight | tonne km | 0.07547 kg CO2e / tkm | DEFRA 2024, articulated HGV, average laden |
| 3, category 6 | Business air travel | passenger km | 0.27257 kg CO2e / pkm | DEFRA 2024, domestic flight with radiative forcing |

Emissions (t CO2e) = activity x factor / 1000. Energy (GJ) uses 3.6 MJ/kWh, 35.78 MJ/L for diesel and 47.3 MJ/kg for LPG.

## Data quality process
1. **Completeness:** every site must submit every month; duplicates are removed (first submission kept).
2. **Validity:** negative readings are rejected; a reading about 1/1000 of the site's usual month is treated as
   MWh entered as kWh and converted; recycled waste above total waste is rejected.
3. **Reconciliation:** electricity per site and quarter must agree with the utility bill within 2%. The bill is the
   source of truth; a missing month is filled from the bill remainder, and a quarter outside tolerance is aligned to
   the bill.
4. **Estimation:** any value still missing is estimated from the site's own monthly average (recycled waste from the
   site's own recycling ratio). Every estimate is flagged in the workbook (`Estimated fields` column).

Every action is written to the Validation Log sheet with stage, check, site, period, detail and action taken.

## KPIs and targets (FY 2025-26)
| KPI | Target |
|---|---|
| Scope 1 and 2 intensity (kg CO2e per sq ft) | 5% below FY 2024-25 |
| Renewable electricity share | at least 12% |
| Waste diversion (recycled share of waste) | at least 65% |
| Water intensity (kl per sq ft) | 3% below FY 2024-25 |
