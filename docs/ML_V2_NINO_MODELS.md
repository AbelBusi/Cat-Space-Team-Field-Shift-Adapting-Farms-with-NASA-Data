# Field Shift ML · v2 models with the Niño 1+2 index

Status (Nov 15, 2026): **trained and validated. No v2 model replaces v1.** Soil water: no difference on Validation, the
decision waits for 2026. NDVI: rejected by the rules (§4). Nothing from Phases 1–3 or the v2 intervals experiment is
modified: the tested v1 models and `ml/artifacts/final_model/` stay as they are (SHA-256 checked in the notebook).
Notebook: [`ml/notebooks/05_v2_nino_models.ipynb`](../ml/notebooks/05_v2_nino_models.ipynb); outputs:
`ml/artifacts/v2_nino_models/`. The rules in §3 were committed before training (commit `7843f08`).

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

## 4. Results

**The index in each period** (months above +1 °C / above +2 °C): Training 1998–2017: 22 / 12 (1998, 2015–16, 2017).
Validation 2018–2022: 0 / 0 (calm years, maximum +0.79 °C). Testing 2023–2025: 11 / 5 (the 2023 coastal El Niño, peak
+2.55 °C). No Niño input in 2023–2025 is outside its 1998–2017 range.

### 4.1 Validation 2018–2022 (this decides)

| | Soil water (m³/m³) | NDVI |
|---|---|---|
| RMSE v1 → v2 | 0.0125 → 0.0126 | 0.103 → 0.104 |
| Skill of v2 over v1 [95 % CI] | −0.009 [−0.031, 0.010] | −0.013 [−0.021, −0.005] |
| Criteria A–F | all pass (F: 0.885) | **E fails**: one province with skill −0.016 vs climatology (v1: +0.01) |
| Trees | 2,171 (v1: 1,122) | 107 (v1: 89) |
| **Verdict (rules of §3)** | **No clear difference: the decision waits for 2026** | **Rejected** (fails E, and slightly worse than v1) |

On calm years the index adds nothing to soil water, and it adds a little noise to NDVI. This is the overfitting risk
stated in §3: with only a few events in Training, the index partly works as a label for those years.

### 4.2 Second look at 2023–2025 (already seen by Phase 3: cannot decide anything)

| | Soil water v1 → v2 | NDVI v1 → v2 |
|---|---|---|
| RMSE 2023–2025 | 0.0198 → **0.0185** (skill +0.065 [0.039, 0.092]) | 0.126 → **0.121** (skill +0.045 [0.025, 0.066]) |
| Year 2023 | 0.023 → 0.020 | 0.142 → 0.125 |
| Peak of the El Niño | **March 2023: 0.053 → 0.039**, bias −0.037 → −0.025 | **Q2 2023: 0.221 → 0.182**, bias −0.152 → −0.102 |
| Calm years | 2024: 0.019 → 0.019 · 2025: 0.017 → 0.016 | 2024: 0.115 → 0.112 · 2025: 0.120 → 0.124 |
| May 2024 (rain without El Niño) | 0.027 → 0.027 (not fixed) | — |
| 90 % range with monthly recalibration | 90 % (v1) → **87 %** (v2): v2 is narrower (± 0.025 vs ± 0.032), and γ = 0 was chosen on calm Validation | 87 % → 87 % |

- **The index does what it should in the El Niño months:** it cuts the March 2023 soil water error by about a quarter and
  the Q2 2023 NDVI error by about a fifth. It does not help in other wet months (May 2024), which need the rain data (§2).
- In the model the index is a small input: 0.6 % of the soil water model's gain in total (the last months of soil water explain
  88 %), 8 % of the NDVI model's gain.
- Figure: `ml/artifacts/v2_nino_models/v2_nino_error_timeline.png` (error per month or quarter, v1 vs v2, with the index).

### 4.3 What this means

- **v1 stays the standard model** (`final_model/`), with the v2 range method of the intervals experiment as the proposed
  way to show uncertainty.
- **Soil water v2 (with Niño)** is kept as a candidate. 2026 is the right test: it has a strong coastal El Niño
  (+3.85 °C in September 2026, stronger than 2023). When the complete 2026 data arrive, both models are run once on 2026
  and compared with the same rules; if v2 is clearly better there, it can replace v1 (the team decides).
- **NDVI v2 is rejected** by the rules written before training. It looked better on 2023–2025, but that period cannot be
  used to decide, and on Validation it was worse.
- The rules were not changed after seeing results, and no other variant was tried.

## 5. Next data

| # | Data | Status |
|---|---|---|
| 1 | Niño 1+2 | received and used |
| 2 | ERA5-Land monthly `total_precipitation` and `volumetric_soil_water_layer_2`, 1998–2026, with the request of §2 | the GRIB received is the wrong product (hourly, one hour per day). Please re-request; the 2005–2026 hourly files in the queue are not needed |
| 3 | Land cover or irrigated area per year | pending |
| 4 | 2026, once complete | pending: the decisive test for soil water v2 |

**Is ERA5 rain essential?** Not for the prototype. The soil water model already explains 96–99 % of the variation; ERA5's
own rain is aimed at single storm months such as May 2024, which the Niño index does not fix.
It is the next improvement, not a blocker. A provisional fill for 2005–2025 is not recommended: a gap filled from CHIRPS
only repeats CHIRPS, and a gap filled from another reanalysis would be a different variable from the one used in 1998–2004.
