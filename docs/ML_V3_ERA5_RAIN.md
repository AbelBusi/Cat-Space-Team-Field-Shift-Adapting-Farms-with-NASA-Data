# Field Shift ML · v3 soil water model with ERA5-Land's own rain

Status (Nov 15, 2026): **rules written, model not trained yet.** The tested v1 models and `ml/artifacts/final_model/`
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
