# Field Shift ML · v2 models with the Niño 1+2 index

Status (Nov 15, 2026): **rules written, models not trained yet.** Nothing from Phases 1–3 or the v2 intervals experiment
is modified: the tested v1 models and `ml/artifacts/final_model/` stay as they are. Outputs will go to
`ml/artifacts/v2_nino_models/`.

## 1. New data received

| File | What it is | Use |
|---|---|---|
| `nino12.long.anom.csv` (NOAA PSL monthly time series) | Niño 1+2 sea surface temperature anomaly (°C), the ocean box off northern Peru. Monthly, Jan 1870 – Sep 2026, one value per month (the same for every cell). | **Used.** Complete for 1998–2025. |
| `c24964fbbed829c38eca7ff421c7fb36.grib` (Copernicus CDS) | **ERA5** (not ERA5-Land), 0.25°, 8 × 9 points, 1998–2004, `tp` (total precipitation) and `swvl2` (soil water 7–28 cm), **one hour per day** (valid 00:00 UTC). | **Not used** (see §2). |

Irregularity in the Niño file: its header says the missing value is `-99.99`, but Oct–Dec 2026 are coded `-9999.000`.
Both are read as missing. The reference period of the anomaly is not stated in the file (to confirm on the PSL page).

## 2. Why the ERA5 file cannot be used yet

- The request downloaded the **hourly** ERA5 product with only the 00:00 UTC time. So `tp` is the rain of **one hour per
  day** (18:00–19:00 in Peru), not the day's rain. Summed over a month and multiplied by 24 it gives about 955 mm a year
  for the area, against 220 mm from CHIRPS (correlation 0.81, but 4× too much, because the evening is the rainy hour).
  It is a biased sample, not a monthly total.
- It covers only 1998–2004. A feature that is missing for 2005–2025 cannot be learned in Training (1998–2017) or checked in
  Validation and Testing. Filling the gap from CHIRPS would only copy CHIRPS, which the model already has.
- It is ERA5 at 0.25° (≈ 28 km), not ERA5-Land at 0.1°, which is the model that produced the soil water target.

**What to download instead (one small request, usually minutes):** CDS dataset `reanalysis-era5-land-monthly-means`,
product type `monthly_averaged_reanalysis`, variables `total_precipitation` and `volumetric_soil_water_layer_2`, years
1998–2026, all months, time `00:00`, area North −5.3, West −80.8, South −7.3, East −78.9, format GRIB or NetCDF.
Unit trap: in the monthly means, `total_precipitation` is the **mean daily** amount in metres; monthly mm =
value × days in the month × 1000. The same data are in Google Earth Engine as `ECMWF/ERA5_LAND/MONTHLY_AGGR`
(`total_precipitation_sum`, already a monthly sum), which can be exported with the same script as the other GEE tables.

## 3. Rules written before training (do not edit after seeing results)

**What changes from v1.** Only new input columns; the targets, the other features, hyperparameters, seed, the early
stopping protocol (fit 1998–2015, stop on 2016–2017, refit on 1998–2017 with the best number of trees) and the baselines
are the same as v1.

| Model | New features |
|---|---|
| Soil water, monthly | `nino12_anom` (same month), `nino12_anom_lag1` (previous month), `nino12_anom_3m` (mean of the last 3 months) |
| NDVI, quarterly | `q_nino12_anom` (mean of the quarter), `q_nino12_anom_lag1` (previous quarter) |

Using the same-month value matches the other inputs: the models already use that month's rain and temperature (they
describe a month, they do not forecast it).

**Validation 2018–2022 decides.**
1. v2 must pass criteria A–E of Phase 1 §10 with the same thresholds, and F with its own split conformal width
   (calibrate on 2018–2020, check on 2021–2022).
2. Skill of v2 over v1 = 1 − RMSE(v2) / RMSE(v1), with a 95 % block-bootstrap CI (same 0.2° blocks):
   - lower CI > 0: **better** on Validation. v2 becomes a candidate to replace v1 (the team decides).
   - CI contains 0: **no difference** on the calm validation years (no strong El Niño in 2018–2022). The decision waits
     for 2026, which has a strong coastal El Niño (Niño 1+2 = +3.85 °C in Sep 2026).
   - upper CI < 0: **worse**. v2 is rejected.

**2023–2025: report only.** Those years were already seen by the Phase 3 test, so they cannot decide anything. Reported:
overall metrics, 2023, March 2023 (soil water) and Q2 2023 (NDVI), the coverage of the 90 % range with monthly
recalibration (the v2 intervals experiment method, γ chosen on Validation), and where the Niño inputs are outside their
1998–2017 range.

**Overfitting risk stated in advance.** The index has one value per month for all cells, and 1998–2017 holds only two
coastal El Niño events (1998 and 2017). The trees could use it to memorize those two years. Rule 2 on years without a
strong event and the 2026 check guard against that.
