# Field Shift ML · Phase 2: Validation (2018–2022)

Status (Nov 15, 2026): **Validation done. Both models pass the acceptance criteria** written in
[`ML_PHASE1_TRAINING.md` §10](ML_PHASE1_TRAINING.md) before these years were loaded. Testing (2023–2026) has not been run.

Notebook: [`ml/notebooks/02_phase2_validation.ipynb`](../ml/notebooks/02_phase2_validation.ipynb). Results:
`ml/artifacts/phase2_validation/` (one folder per model, with CSV tables and `validation_report.json`).

## 1. What was done

- The Phase 1 models were loaded **frozen** (same `model.ubj`, SHA-256 recorded): nothing was refit, tuned or changed.
- The validation tables were built with the same `fs_ml` code as Training. Inputs: the GEE monthly and quarterly tables for
  2018–2022 (2017 read only as history for the lags of January 2018 and Q1 2018; its targets are not scored) and the
  four new NASA POWER files for 2018–2022.
- Baselines: **persistence** (last month / last quarter) and **climatology** (mean per cell and month / quarter, fitted on
  1998–2017). The better of the two is the one each model must beat.
- **95 % confidence intervals** for every metric by block bootstrap: 1,000 resamples of the 61 spatial blocks of 0.2°
  (≈ 22 km, larger than one ERA5-Land pixel), each block carrying its five years. Neighbour cells that repeat the same
  ERA5-Land value are therefore not counted as independent evidence.

## 2. New NASA POWER files: checks

| File | Rows | Duplicates | `-999` | Same grid as 1998–2017 | Range 2018–2022 | Range 1998–2017 |
|---|---|---|---|---|---|---|
| Temperature at 2 Meters (T2M, °C) | 100 | 0 | 0 | yes (20 points) | 12.87–28.97 | 12.13–29.35 |
| Relative Humidity at 2 Meters (RH2M, %) | 100 | 0 | 0 | yes | 47.50–97.38 | 46.42–97.13 |
| Wind Speed at 2 Meters (WS2M, m/s) | 100 | 0 | 0 | yes | 1.00–5.75 | 1.02–6.02 |
| All Sky Surface Shortwave Downward Irradiance (MJ/m²/day) | 30 | 0 | 0 | yes (6 points) | 10.30–24.65 | 9.20–25.80 |

All four cover 01/01/2018–12/31/2022 and join every validation row (no missing POWER value). NDVI coverage in 2018–2022
is complete (2,396–2,582 of 2,585 cells every quarter), unlike 2001–2013.

## 3. Results (validation 2018–2022, 95 % CI)

**Soil water, layer 28–100 cm** (m³/m³, 187,560 rows, 3,126 cells)

| Model | MAE | RMSE | R² | Bias |
|---|---|---|---|---|
| **XGBoost** | **0.0073** [0.0061, 0.0084] | **0.0125** [0.0110, 0.0139] | **0.986** [0.981, 0.990] | −0.0004 [−0.0009, 0.0000] |
| Persistence (best baseline) | 0.0139 [0.0106, 0.0175] | 0.0260 [0.0222, 0.0294] | 0.940 | 0.0002 |
| Climatology | 0.0212 [0.0189, 0.0236] | 0.0317 [0.0280, 0.0352] | 0.911 | 0.0074 |

RMSE skill vs persistence **0.52 [0.48, 0.55]** (it halves the error of repeating last month); MAPE 3.7 %.

**NDVI** (index, 50,477 rows, 2,584 cells)

| Model | MAE | RMSE | R² | Bias |
|---|---|---|---|---|
| **XGBoost** | **0.075** [0.070, 0.079] | **0.103** [0.097, 0.109] | **0.66** [0.60, 0.72] | 0.002 [−0.006, 0.008] |
| Climatology (best baseline) | 0.089 [0.080, 0.098] | 0.126 [0.111, 0.141] | 0.50 | −0.031 |
| Persistence | 0.107 [0.094, 0.120] | 0.156 [0.141, 0.170] | 0.22 | 0.005 |

RMSE skill vs climatology **0.18 [0.10, 0.25]**.

**By year, province and season** (skill vs the best baseline, 95 % CI; full tables in `metrics_by_*.csv`):

| | Soil water | NDVI |
|---|---|---|
| Worst year | 2022: 0.45 [0.41, 0.48] | **2018: 0.06 [−0.04, 0.15]** |
| Best year | 2019: 0.65 [0.63, 0.68] | 2020: 0.21 [0.11, 0.29] |
| Chiclayo · Ferreñafe · Lambayeque | 0.28 · 0.57 · 0.47 | 0.17 · **0.01 [−0.04, 0.05]** · 0.24 |
| Season | wet Jan–Apr 0.44 · dry May–Dec 0.61 | Q1 0.18 · Q2 0.12 · Q3 0.20 · Q4 0.26 |

## 4. Prediction intervals (how sure a single prediction is)

Split conformal: the absolute errors of 2018–2020 set the width, then 2021–2022 checks how often the truth falls inside.

| Nominal | Soil water: width (±) | Coverage 2021–2022 [95 % CI] | NDVI: width (±) | Coverage 2021–2022 [95 % CI] |
|---|---|---|---|---|
| 80 % | 0.010 | 0.76 [0.71, 0.81] | 0.116 | 0.77 [0.74, 0.79] |
| 90 % | 0.017 | **0.87** [0.84, 0.90] | 0.164 | **0.88** [0.86, 0.90] |
| 95 % | 0.027 | 0.93 [0.92, 0.95] | 0.213 | 0.94 [0.93, 0.95] |

- The Phase 1 provisional widths (± 0.031 and ± 0.25 at 90 %) turned out **too wide**: they covered 96–97 % of 2018–2022.
- Intervals are slightly **short of their nominal level** (87–88 % for 90 %), worst in the rainy season for soil water
  (85 %) and in Q3 for NDVI (84 %). One width per season (Mondrian conformal) helps soil water in the dry season (88 %)
  but not enough in the wet season.
- Final widths calibrated on all of 2018–2022, for Testing and the app, are in each `validation_report.json`:
  soil water ± 0.019 m³/m³ (dry season ± 0.013, wet season ± 0.030) and NDVI ± 0.17 at 90 % (Q1 ± 0.18, Q2 ± 0.20,
  Q3 ± 0.15, Q4 ± 0.12). Testing will report their real coverage on
  2023–2026, a period that includes the 2023 coastal El Niño.

## 5. Inputs outside the training range

About 15–16 % of validation rows have at least one input outside the 1998–2017 p01–p99 range (mostly relative humidity
and temperature; 0.3 % / 1.4 % outside the absolute min–max). Soil water error is no worse on those rows
(RMSE 0.011 vs 0.013); NDVI error is a little worse (0.113 vs 0.101). The app must keep warning on them.

## 6. Acceptance criteria

| # | Rule | Soil water | NDVI |
|---|---|---|---|
| A | Skill vs best baseline ≥ 0.20 (soil) / 0.10 (NDVI) | 0.52 ✅ | 0.18 ✅ |
| B | Lower 95 % CI of that skill > 0 | 0.48 ✅ | 0.10 ✅ |
| C | RMSE ≤ 0.04 m³/m³ (soil; NDVI report only) | 0.0125 ✅ | 0.103 |
| D | \|bias\| ≤ 0.01 (soil) / 0.03 (NDVI) | 0.0004 ✅ | 0.002 ✅ |
| E | Skill ≥ 0 in every year and province | worst 0.28 ✅ | worst 0.01 ✅ (CI crosses 0) |
| F | 90 % interval coverage on 2021–2022 in [0.87, 0.93] | 0.872 ✅ (edge) | 0.880 ✅ |
| G | Share outside training p01–p99 (report) | 15 % | 16 % |

**Verdict: both models are accepted** and may feed the simulator, with the recalibrated intervals.

Read with care:
- **NDVI passes by a small margin.** The lower CI of its skill sits exactly at the A threshold (0.10); in 2018 and in
  Ferreñafe the model is not clearly better than climatology (CI crosses 0). For a farmer it means: "a bit better than the
  usual value for this place and season", not a strong forecast. Without irrigation or crop calendars in the inputs it
  cannot do much more.
- **Soil water coverage (F) passes at the edge** (0.872 vs 0.87). Intervals in the rainy season are too narrow; showing
  one width per season is the safer option for the app (a presentation choice, not a model change).
- Validation years were calmer than 2017: no strong coastal El Niño. Testing (2023) will be the real stress test.
- Nothing was tuned, so no decision was made on these years beyond the pre-written rules.

## 7. VPD and GDD

The models **do not compute VPD** (vapour pressure deficit, from temperature and relative humidity) **or GDD** (growing
degree days, from temperature and each crop's base and ceiling temperatures). Those appeared in an earlier AI chat, not in
this code. The team decided not to derive them: they need crop thresholds and sampling that we do not have yet, so they
stay out until they are measured and documented.

## 8. Irregularity found in this phase

**37 % of the grid lies outside Lambayeque.** Of the 3,149 cells, 1,176 fall outside the department's OpenStreetMap
boundary (584 north of −6.0°, towards Piura; 506 east of −79.3°, towards Cajamarca; the rest south, towards La Libertad).
They were kept (their data are valid) and reported as "outside" in the per-province tables. Question for the exporter:
which region or mask defines the GEE grid?

## 9. Next: Testing (2023–2026)

Needed first: **NASA POWER 2023–2026** for the same 4 parameters and grid (CHIRPS is also missing in 2026-10 in the GEE
table). Then run once with the frozen models and the intervals saved here, report the same metrics and coverage, and
change nothing afterwards.
