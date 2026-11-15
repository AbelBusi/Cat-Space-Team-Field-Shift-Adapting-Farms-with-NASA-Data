# Field Shift ML · v3 soil water model with ERA5-Land's own rain

Status (Nov 15, 2026): **trained and validated: R1 and R2 pass, so v3 may run simulations** (rules committed before training in `8d87fe5`; notebook `ml/notebooks/08_v3_era5_rain.ipynb`). The tested v1 models and `ml/artifacts/final_model/`
are not changed. Outputs will go to `ml/artifacts/v3_era5_rain/`.

## 1. New data received

`GEE_2km_ERA5L_lluvia_capa2_1998_2026.csv` (Google Earth Engine, `ECMWF/ERA5_LAND/MONTHLY_AGGR`, exported with
`coveringGrid` at 2 km over a rectangle: 9,016 cells × 346 months, 1998-01 → 2026-10, 3.1 M rows, no duplicates).

| Check | Result |
|---|---|
| Our 3,149 grid cells | all present (ids `x,y` identical) |
| Missing values | 22 coastal cells with no value in any month (ERA5-Land land–sea mask, as for soil water) |
| `volumetric_soil_water_layer_2` (7–28 cm) | coherent: r = 0.94 with layer 3; between layers 1 and 3 (± 0.02) in 92 % of cell-months |
| `total_precipitation_sum` (m per month → mm) | tracks CHIRPS over time (r = 0.81 for the monthly grid mean, 0.54 cell by cell) but is **3–6 times larger**: grid-mean yearly rain 923 mm vs 221 mm (CHIRPS) in 2000, 3,069 vs 337 in 1998, 650 vs 153 in 2024 |

**Irregularity.** The ERA5-Land rain is much wetter than CHIRPS on this desert coast (a known wet bias of the
reanalysis over the coast and the Andes; the hourly GRIB received earlier gave the same order, ~955 mm/year). It is
not a unit error. It is the rain that drives the ERA5-Land soil water we predict, so it is used **as a model input
only**; it must never be shown to users as "the rain".

## 2. Rules written before training (do not edit after seeing results)

**Model v3 (soil water only; the NDVI model stays v1).**

- Features: the 19 v1 features **plus** `era5_rain_mm`, `era5_rain_mm_lag1`, `era5_rain_mm_lag2`, `era5_rain_mm_sum6`
  (built like the CHIRPS ones, inside each cell). Layer 2 is **not** used: a same-month value would be next to the
  target, and a lagged one would be another state the projections cannot predict.
- **Monotone constraints** (XGBoost `monotone_constraints`): +1 for the 8 rain features (more rain never lowers the
  prediction), −1 for `pet_mm` and `t2m_c` (more evaporative demand or heat never raises it). All other features free.
- Everything else as v1: target, hyperparameters, seed 42, fit 1998–2015, early stopping on 2016–2017, refit on
  1998–2017, same baselines.

**Decision (Validation 2018–2022 decides; 2023–2025 is a second look).**

| # | Rule | Consequence |
|---|---|---|
| R1 | Criteria A–F of `ML_PHASE1_TRAINING.md` §10, same thresholds (F with its own split conformal width) | fail → v3 rejected |
| R2 | Not clearly worse than v1: the **upper** 95 % CI of the RMSE skill of v3 over v1 is ≥ 0 (block bootstrap) | fail → v3 rejected |
| R3 | The scenario checks S1–S4 of `ML_API_VALIDATION.md`, same rules and starts, rerun with v3 | each passing check lets that what-if leave the `experimental` label **when v3 runs it** |
| R4 | Projection hindcasts for v3 (as `ML_PROJECTIONS.md` §3: starts Dec 2017–Nov 2022, leads 1–12, analog years 1998–2017) | gives v3's useful lead and range corrections; needed before v3 can run simulations |
| R5 | 2023–2025 metrics, March 2023 and the 90 % coverage | report only |

If R1 and R2 pass, the API may run **simulations** with v3 (with v3's own range corrections from R4); one-step
predictions and the web's projections stay v1 until the team decides. If R1 or R2 fails, v3 is not used.
2026 cannot be scored yet: ERA5-Land reaches 2026-10, but NASA POWER and the GEE tables for 2026 are incomplete.

## 3. Results

| | v1 | **v3** |
|---|---|---|
| Trees | 1,122 | 1,877 |
| Validation 2018–2022 RMSE | 0.0125 | **0.0099** m³/m³ |
| Skill vs persistence (A, B) | 0.52 [0.48, 0.55] | **0.62 [0.59, …]** |
| Skill of v3 over v1 (R2) | — | **+0.21 [0.17, 0.25]**: clearly better, not just "not worse" |
| Criteria A–F (R1) | pass | **pass** (bias 0.0013, worst year 0.56, worst province 0.44, 90 % coverage 2021–2022 0.884) |
| 2023–2025 RMSE (second look) | 0.0198 | **0.0142** (skill over v1 +0.28 [0.24, 0.32]) |
| March 2023 (coastal El Niño) RMSE · bias | 0.053 · −0.037 | **0.024 · −0.007** |
| 90 % coverage 2023–2025, one width per season | 82 % | 82 % |
| Gain from last month's soil water · surface · rain | 68 % · 24 % · 2.4 % | 65 % · 22 % · **8.3 %** (8.0 % ERA5-Land rain, 0.3 % CHIRPS) |

**Projections (R4).** Useful lead **6 months** (the same as v1; skill 0.43 at lead 1 vs persistence, 0.17 at lead 2 vs
climatology). Coverage of the 90 % band in 2023–2025: 81 %, still too narrow in an El Niño period.

**Scenario checks with v3 (R3)** — same rules as `ML_API_VALIDATION.md`:

| Check | v1 | **v3** |
|---|---|---|
| S1 temperature ±2 °C | fail (9.7 % wrong way) | **pass**: 0 % wrong way; +2 °C lowers soil water by 0.003 on average, −2 °C raises it by 0.003 |
| S2 droughts of 1–6 months | fail (5–6 months) | **pass**: −0.007, −0.019, −0.030, −0.039, −0.046, −0.052 m³/m³ at the end of the drought; ≤ 0.01 % of cells rise |
| S3 rain × 0.5 / × 2 | fail (effect ±0.0006) | **pass**: −0.012 / +0.019 m³/m³, no cell the wrong way |
| S4 recovery after 3 dry months | fail (83 %) | **fail** (76 %): the drought's effect fades by month 12 on average (−0.030 → −0.007), but not in ≥ 90 % of cells |

**Reading.** Giving the model the rain that actually drives ERA5-Land, with monotone constraints, fixed the two
weaknesses found in Phase 2: storm months (March 2023 error halved) and the response to changed weather (temperature,
droughts and rain now move soil water the right way, by a visible amount). Recovery stays experimental. The intervals are
still too narrow in El Niño years. Per §2, the API may run **simulations** with v3; the web's projections and one-step
predictions stay v1 until the team decides. ERA5-Land rain remains an input only.
