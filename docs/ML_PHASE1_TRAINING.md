# Field Shift ML · Phase 1: Training (1998–2017)

Status (Nov 15, 2026): **Training done. Validation (2018–2022) done afterwards with these frozen models: both pass, see
[`ML_PHASE2_VALIDATION.md`](ML_PHASE2_VALIDATION.md). Testing (2023–2026) not run.** During Training no row from those
years was used to fit, tune or choose anything. Every number below is an **internal training diagnostic**, not the accuracy the
models will have on new years.

Notebook: [`ml/notebooks/01_phase1_training.ipynb`](../ml/notebooks/01_phase1_training.ipynb) (run locally; how-to in
[`ml/README.md`](../ml/README.md)). Shared code for all phases: `ml/fs_ml/`. Saved models: `ml/artifacts/phase1_training/`.

## 1. Summary

| | Soil water model | Vegetation model |
|---|---|---|
| Target | `sm_root_m3m3`: ERA5-Land soil water, layer 3 (28–100 cm), month *t* | `ndvi`: satellite NDVI of quarter *q* |
| Unit | m³/m³ | index (−1 to 1) |
| Rows (1998–2017) | 750,240 (3,126 cells × 240 months) | 91,224 (2,585 cells, 62 quarters with images) |
| Trees (early stopping) | 1,122 | 89 |
| Internal RMSE 2016–2017 | 0.022 m³/m³ | 0.145 |
| RMSE skill vs best simple baseline | **+0.48** (vs persistence) | **+0.08** (vs climatology) |
| Provisional 90 % interval | ± 0.031 m³/m³ | ± 0.25 |
| Reading | Clearly better than the baselines | **Weak**: barely beats "same as the usual NDVI for that cell and season" |

Not trained, on purpose: NDSI (undocumented formula), crop yield, crop type per cell, rotation choice and risk classes
(no reference labels exist in our data). See §4.

## 2. Datasets inspected

| File (team folder *Datos para proyecto Nasa*) | What it really contains | Coverage | Used |
|---|---|---|---|
| `Hídrico/GEE_2km_Clima_Humedad_Mensual_1998_01_a_2026_11.csv` (499 MB) | 3,149 cells of 2 km × 346 months. `lluvia_chirps_mm` (CHIRPS, mm/month), `temperature_2m` (K), `potential_evaporation_sum` (m, negative), `volumetric_soil_water_layer_1` and `_3` (m³/m³, ERA5-Land), `max` (always 1), `.geo` (polygon) | 1998-01 → 2026-10 | Yes, 1998–2017 only |
| `Hídrico/GEE_2km_Veg_Salinidad_Trimestral_1998_Q1_a_2026_Q4.csv` (72 MB) | `NDVI`, `NDSI_Salinidad` per 2 km cell and quarter (`fecha_trimestral` = first month), `max` (always 1) | 98 quarters, 1998 → 2026, with gaps | NDVI yes; NDSI no |
| `Hídrico/Lambayeque_Grilla_2km.csv` (70 MB) | **Sentinel-2 scenes** (tile + time in the id), NDVI and NDSI per cell and date | 2023-01-01 → 2024-12-29 | **No**: all rows are Testing years |
| `Clima y metereología/*` (4 NASA POWER CSVs) | T2M (°C), RH2M (%), WS2M (m/s) on a 0.5° × 0.625° MERRA-2 grid (20 points); ALLSKY_SFC_SW_DWN (MJ/m²/day) on a 1° CERES grid (6 points). Wide format with an ANN column | 1998–2017 | RH2M, WS2M, ALLSKY as features; T2M kept but not a feature |
| `Suelos/*.json` (9 FAO GAEZ layers) | Class codes on a 5′ (~9 km) grid of Peru (151 × 219, 15,352 pixels each) | static | 5 layers as features |
| MIDAGRI producer register exports (18 `.xlsx` in Downloads) | District, tenure and main crop per producer; no coordinates, dates or yields | — | No (see §3.8) |

Conversions only (no derived variables): K → °C, potential evaporation m (negative = upward) → mm positive, NASA POWER
wide → long with ANN dropped, `-999` → missing. Cell centers come from the ids (`x,y` × 0.0179663°); they match the GEE
polygons to 1e-14°.

## 3. Irregularities found and what was done

Questions marked **(team)** need an answer from whoever exported the data.

1. **`Lambayeque_Grilla_2km.csv` is not a climate or soil table.** It holds Sentinel-2 scenes from 2023–2024 (NDVI, NDSI).
   It falls entirely in the Testing years, so it was not opened beyond its dates. An earlier AI chat described it with columns
   (`humedad_raices_m3m3`, `elevation`, wind, radiation) that **do not exist in any file**; it also gave model metrics that were
   never computed. Do not reuse numbers from that chat.
2. **The monthly table has soil layers 1 and 3, not 2.** ERA5-Land layer 3 is **28–100 cm** (layer 1: 0–7 cm). There is no
   elevation, wind or radiation in the GEE tables.
3. **23 coastal cells have no ERA5-Land value in any month** (land/sea mask of the 9 km product). They are left out of the soil
   water model (target missing). CHIRPS is missing for all cells in 2026-10 (outside Training; note for Testing).
4. **NDVI gaps.** 18 of the 80 quarters of 1998–2017 have no image at all (all of 2012, most of 2002, 2009, 2010). From 2001-Q3
   to 2013-Q1 most quarters cover only 10–20 % of the cells, and two quarters cover 1 and 3 cells. Full coverage returns in
   2013-Q2, when Landsat 8 data start, which suggests a Landsat composite, but the sensor and compositing method are not
   written anywhere **(team)**. Done: all observed values kept, nothing imputed; lags are missing when that quarter has no image.
5. **Only 2,585 of the 3,149 cells ever have NDVI.** The mask behind this (cropland? valid pixels?) is not documented **(team)**.
6. **`NDSI_Salinidad` behaves like a vegetation or moisture index, not a salinity index:** Pearson r = +0.82 with NDVI
   (salinity indices usually fall where vegetation grows). Without its formula it is neither a target nor a feature **(team)**.
7. **FAO GAEZ.** "Low" and "High" files are identical pixel by pixel for lime/gypsum, salinity/sodicity and rooting conditions
   (all of Peru); Oxygen Availability High has one single value (10) in Lambayeque; Nutrient Availability exists only as "low".
   The files carry class codes 2–13 but no legend (codes 11 and 13 appear in Peru, not in Lambayeque) **(team: which GAEZ
   v4 theme and input levels were downloaded, and the legend)**. Done: 5 distinct layers used as codes (trees only split them,
   nothing is averaged); duplicates and the constant layer left out.
8. **MIDAGRI exports:** the 18 files are 3 unique tables (Chiclayo ×5, Lambayeque ×7, Ferreñafe ×6 identical copies). Each has
   exactly 2,000 rows, the export limit of the viewer, so they are **truncated**. No coordinates, campaign dates or production:
   they cannot label crop type per cell or yield. Not used.
9. **NASA POWER files are clean** (no `-999`, no duplicates) but stop in 2017. **Validation and Testing need the same 4 files for
   2018–2026** on the same grid, or the soil water and NDVI models cannot be evaluated **(team)**.
10. **Repeated values between neighbours.** One ERA5-Land pixel (~9 km) covers about 20 cells of 2 km; CHIRPS (~5.5 km) about 8.
    The effective sample is far smaller than the row count, so rows are never split at random.
11. Minor, kept as is: CHIRPS has floating-point dust (values like 1e-14 mm); 233 rows have surface soil water below
    0.005 m³/m³ (desert cells); 342 NDVI values are negative (water, wet sand); robust z-scores flag many rain months only
    because the desert median is near zero. No value is outside a physical range.

## 4. Targets and features

**Soil water model** — what the soil water of month *t* is, given the weather of month *t*, the months before it and the soil
state of month *t − 1*. This design lets the simulator change the weather of a month and see the model's response.

| Feature | Unit | Source |
|---|---|---|
| `rain_mm`, `rain_mm_lag1`, `rain_mm_lag2`, `rain_mm_sum6` (t−5…t) | mm | CHIRPS (2 km table) |
| `t2m_c`, `pet_mm`, `pet_mm_lag1` | °C, mm | ERA5-Land |
| `sm_root_m3m3_lag1`, `sm_surface_m3m3_lag1` | m³/m³ | ERA5-Land, previous month |
| `power_rh2m_pct`, `power_ws2m_ms`, `power_allsky_mj_m2_day` | %, m/s, MJ/m²/day | NASA POWER (nearest point) |
| `month_sin`, `month_cos` | — | calendar |
| 5 soil classes (`soil_*_class`) | code | FAO GAEZ (nearest pixel) |

**Vegetation model** — NDVI of quarter *q* from that quarter's weather and the NDVI seen 1 and 4 quarters earlier.
Features: `q_rain_mm`, `q_rain_mm_lag1`, `q_t2m_c`, `q_pet_mm`, `q_sm_root_m3m3`, `q_power_rh2m_pct`, `q_power_ws2m_ms`,
`q_power_allsky_mj_m2_day`, `quarter`, `ndvi_lag1`, `ndvi_lag4`, and the 5 soil classes.

No derived agronomic indices: **VPD** (vapour pressure deficit) and **GDD** (growing degree days, which need each crop's
base temperature) are not computed. They need crop thresholds and field sampling we do not have; an earlier AI chat proposed
them, the team decided against it.

Never features: cell id, latitude, longitude, year (the model must learn from conditions, not memorize places or years).
The target is never shifted forward, and no feature uses a later period than the target.

## 5. Partitions

| Set | Years | Use |
|---|---|---|
| Training | 1998–2017 | Phase 1 (this document) |
| ↳ internal fit | 1998–2015 | Fit the trees |
| ↳ internal early stopping | 2016–2017 | Choose the number of trees; provisional intervals |
| Validation | 2018–2022 | Phase 2: compare, tune, calibrate. **Not loaded yet** |
| Testing | 2023–2026 | Phase 3: one final run after every decision. **Not loaded yet** |

Chronological blocks, not 70/15/15 random rows (temporal autocorrelation and repeated neighbour values would make a random
split look far better than reality). After early stopping, the final model was **refit on all 1998–2017** with the number of
trees found, so it has seen both coastal El Niño years of the period (1998, 2017).

## 6. Preprocessing

No imputer and no scaler. XGBoost handles missing values itself (start-of-series lags, quarters without an image); filling
them would invent NDVI never observed. Only rows with a missing **target** are dropped. Fitted on training rows and saved:
the feature ranges (min, p01, p50, p99, max) for out-of-range warnings, and the climatology baselines.

## 7. Model configuration

`XGBRegressor`, `objective = reg:squarederror`, `tree_method = hist`, seed 42:

| Hyperparameter | Value | Why |
|---|---|---|
| `n_estimators` | 3000 cap → 1,122 (soil) / 89 (NDVI) | Set by early stopping (100 rounds of patience) on 2016–2017 |
| `learning_rate` | 0.05 | Common moderate value; small steps generalize better |
| `max_depth` | 6 | XGBoost default; enough for weather × soil interactions |
| `min_child_weight` | 20 | Leaves need many rows, against memorizing single cells |
| `subsample`, `colsample_bytree` | 0.8, 0.8 | Row and column sampling against overfitting |
| `reg_alpha`, `reg_lambda`, `gamma` | 0, 1, 0 | Defaults; tuning belongs to Validation |

No hyperparameter search was done (the plan reserves tuning for Validation). Library versions are in each `metadata.json`
(Python 3.14.6, XGBoost 3.4.1, pandas 3.1.1, NumPy 2.5.4, SciPy 1.18.1, scikit-learn 1.9.1).

## 8. Internal diagnostics (training only)

**Soil water** (m³/m³)

| Subset | Model | MAE | RMSE | R² | Bias |
|---|---|---|---|---|---|
| fit 1998–2015 (in-sample) | XGBoost | 0.0040 | 0.0066 | 0.996 | 0.0000 |
| internal 2016–2017 | XGBoost | **0.0116** | **0.0224** | **0.955** | −0.0027 |
| internal 2016–2017 | persistence (last month) | 0.0254 | 0.0428 | 0.836 | −0.0004 |
| internal 2016–2017 | climatology (cell × month) | 0.0265 | 0.0433 | 0.832 | −0.0128 |
| internal 2016–2017 | training mean | 0.0888 | 0.1065 | −0.015 | −0.0128 |

By year: 2016 RMSE 0.0165 (R² 0.97); 2017 (El Niño Costero) RMSE 0.0271 (R² 0.93).

**NDVI** (index)

| Subset | Model | MAE | RMSE | R² | Bias |
|---|---|---|---|---|---|
| fit 1998–2015 (in-sample) | XGBoost | 0.070 | 0.097 | 0.740 | 0.000 |
| internal 2016–2017 | XGBoost | **0.101** | **0.145** | **0.489** | −0.050 |
| internal 2016–2017 | climatology (cell × quarter) | 0.115 | 0.157 | 0.401 | −0.071 |
| internal 2016–2017 | persistence (last quarter) | 0.137 | 0.194 | 0.088 | −0.009 |
| internal 2016–2017 | training mean | 0.171 | 0.213 | −0.093 | −0.062 |

By year: 2016 RMSE 0.117 (R² 0.67); 2017 RMSE 0.169 (R² 0.24, bias −0.09: the model misses the desert greening of the
2017 El Niño Costero; bare desert cells went from NDVI ≈ 0.10 in 2014–2016 to 0.25).

How to read this:
- The gap between in-sample and internal errors (3× for soil water, 1.5× for NDVI) is the expected optimism of training
  metrics. Only Validation will tell the real error.
- Soil water: most of the skill comes from last month's soil state (largest contributions: `sm_root_m3m3_lag1`,
  `sm_surface_m3m3_lag1`), but the model halves the error of simply repeating last month.
- NDVI: only 8 % better than the usual NDVI for that cell and season. Without irrigation, crop calendars or land-use change
  in the inputs (Olmos, Tinajones), the weather explains little of the NDVI. It may fail Validation (§10).
- Contributions (mean |TreeSHAP value|, `ml/artifacts/phase1_training/phase1_diagnostics.png`) describe the model, **not
  causes in the field**.

## 9. Error margins and confidence: what we can and cannot say

- **Error in units.** RMSE and MAE are in the target's unit: on 2016–2017 the soil water model was off by 0.012 m³/m³ on
  average (MAE), the NDVI model by 0.10. RMSE weighs large misses more; R² is the share of variance explained.
- **Skill score** = 1 − RMSE_model / RMSE_baseline (Murphy, 1988). 0 means "no better than the simple rule"; it is the main
  criterion, because R² alone looks high whenever the target has a strong seasonal cycle.
- **Provisional prediction intervals** (split conformal on the 2016–2017 residuals of the model fitted on 1998–2015):

  | Nominal coverage | Soil water (± m³/m³) | NDVI (±) |
  |---|---|---|
  | 80 % | 0.016 | 0.163 |
  | 90 % | 0.031 | 0.252 |
  | 95 % | 0.050 | 0.331 |

  **Check:** intervals calibrated on 2016 alone covered only 81 % (soil water) and 78 % (NDVI) of 2017 at 90 % nominal. Errors
  are larger in El Niño years, so a single global interval is too narrow exactly when it matters. These intervals must not be
  shown to users until Validation recalibrates them (ideally separately for wet and dry seasons or ENSO phases).
- **No confidence percentages.** XGBoost regressors do not produce a probability. The app may show an interval with its
  empirical coverage on held-out years, never a "92 % confidence" made up from the model output.
- **Out-of-range inputs.** Each model saves the training range of every feature (`preprocessing.json`). Any input outside
  p01–p99 gets a warning, outside min–max a strong warning: trees cannot extrapolate (a +4 °C scenario beyond the warmest
  month seen gets the prediction of the warmest month seen).

## 10. Acceptance criteria for Validation and Testing (decided now, before seeing those years)

Thresholds are **team proposals** with the reason next to each; they are written here so nobody moves them after seeing the
results.

| # | Criterion (on 2018–2022) | Soil water | NDVI | Reason |
|---|---|---|---|---|
| A | RMSE skill vs the best baseline (persistence, climatology) | ≥ 0.20 | ≥ 0.10 | XGBoost must earn its complexity over a one-line rule |
| B | Lower bound of the 95 % CI of that skill | > 0 | > 0 | The gain must not be luck. CI by block bootstrap: 1,000 resamples of 0.2° spatial blocks (larger than an ERA5-Land pixel), years kept whole |
| C | RMSE | ≤ 0.04 m³/m³ | report only | 0.04 m³/m³ is the accuracy requirement of NASA's SMAP soil moisture mission (Entekhabi et al., 2010), used as a ceiling |
| D | \|bias\| | ≤ 0.01 m³/m³ | ≤ 0.03 | A systematic shift would mislead every scenario |
| E | Skill in each validation year and each province | ≥ 0 | ≥ 0 | No year or place where the model is worse than the simple rule |
| F | Interval coverage (calibrate on 2018–2020, check on 2021–2022) | 90 % nominal → 87–93 % | same | Intervals must mean what they say |
| G | Out-of-range share of validation rows (outside p01–p99) | report, and metrics on those rows apart | same | Shows where the model is guessing |

Decision rules:
- All of A–F pass → the model can feed the simulator, with intervals recalibrated on all of 2018–2022.
- A or B fails → the app shows the baseline instead (the simpler rule wins). Likely for NDVI as it stands.
- C, D, E or F fails → fix the model (features, monotone constraints on rain and temperature, seasonal intervals),
  using **Validation only**, then re-check.
- Testing (2023–2026, includes El Niño Costero 2023): run **once** after all decisions, report the same metrics and the
  empirical coverage, change nothing afterwards. If Testing fails, say so in the submission.

Also to report in Validation: MAE, RMSE, R², bias per model, baseline, year, province and season (MAPE only for soil water:
NDVI crosses zero), and the predicted vs observed plot.

## 11. Limits: when not to use these models

- **ERA5-Land soil water is a model, not a measurement, and knows nothing about irrigation.** In the Chancay-Lambayeque,
  Olmos or Motupe valleys it describes rain-fed soil, not a watered field. Never present it as "your field's moisture".
- One ERA5-Land value covers ~9 km and one GAEZ class ~9 km: a 2 km cell inherits them. NASA POWER points are 55–110 km apart.
- The models describe associations in 1998–2017. Changing an input in the simulator shows the **model's** response, not a
  proven cause, and not a forecast of a real future.
- No crop, yield, irrigation requirement or risk class is predicted. Those need crop labels, yields and agronomic thresholds
  we do not have (future: FAO AquaCrop with crop data).

## 12. Saved artifacts and reproduction

```
ml/artifacts/phase1_training/
  phase1_summary.json           seeds, splits, versions, headline numbers, what was not trained
  phase1_diagnostics.png        learning curves, predicted vs observed, contributions
  sm_root_monthly/  ndvi_quarterly/
    model.ubj                   final XGBoost model (refit on 1998-2017)
    preprocessing.json          exact feature order, units, missing-value rule, training ranges
    metadata.json               target, hyperparameters, data file SHA-256, partitions, row counts, diagnostics, intervals
    baseline_climatology_by_cell.parquet / _by_season.parquet   baselines fitted on 1998-2017
ml/data/processed/ (not in git, rebuilt by the notebook)
  cells_static.parquet  monthly_panel_1998_2017.parquet  quarterly_panel_1998_2017.parquet
```

Same inputs, seed and library versions give the same models. The raw files are identified by SHA-256 in `metadata.json`.

## 13. Open questions for the team

1. GEE exports: which collections and reducers made the quarterly NDVI (sensor, cloud mask, median or mean?) and what
   formula is `NDSI_Salinidad`?
2. Which mask leaves 564 cells without NDVI?
3. GAEZ: which theme and input levels, and the legend of the codes? Were the identical High/Low files downloaded twice?
4. NASA POWER for the same 4 parameters and grid: 2018–2022 delivered and used in Validation; **2023–2026 still needed
   for Testing**.
5. Licenses: FAO GAEZ data are, as far as we know, CC BY-NC-SA 3.0 IGO (non-commercial) — confirm with the Local Lead like the
   Sentinel-2 basemap (AGENTS.md rule 8).

## References

- Chen, T., Guestrin, C. (2016). XGBoost: A scalable tree boosting system. *KDD '16*, 785–794. doi:10.1145/2939672.2939785
- Funk, C. et al. (2015). The climate hazards infrared precipitation with stations — a new environmental record for monitoring extremes. *Scientific Data* 2, 150066. doi:10.1038/sdata.2015.66
- Muñoz-Sabater, J. et al. (2021). ERA5-Land: a state-of-the-art global reanalysis dataset for land applications. *Earth System Science Data* 13, 4349–4383. doi:10.5194/essd-13-4349-2021
- Entekhabi, D. et al. (2010). The Soil Moisture Active Passive (SMAP) mission. *Proceedings of the IEEE* 98(5), 704–716. doi:10.1109/JPROC.2010.2043918
- Roberts, D.R. et al. (2017). Cross-validation strategies for data with temporal, spatial, hierarchical, or phylogenetic structure. *Ecography* 40, 913–929. doi:10.1111/ecog.02881
- Murphy, A.H. (1988). Skill scores based on the mean square error and their relationships to the correlation coefficient. *Monthly Weather Review* 116, 2417–2424.
- Angelopoulos, A.N., Bates, S. (2021). A gentle introduction to conformal prediction and distribution-free uncertainty quantification. arXiv:2107.07511
- Lundberg, S.M. et al. (2020). From local explanations to global understanding with explainable AI for trees. *Nature Machine Intelligence* 2, 56–67. doi:10.1038/s42256-019-0138-9
- Fischer, G. et al. (2021). *Global Agro-Ecological Zones v4 — Model documentation*. FAO and IIASA. doi:10.4060/cb4744en
