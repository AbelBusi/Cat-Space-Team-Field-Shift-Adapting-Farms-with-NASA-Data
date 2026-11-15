# Field Shift ML · Phase 3: Testing (2023–2025) and final models

Status (Nov 15, 2026): **Testing done, once, on years no decision had seen.** The models are the Phase 1 models,
unchanged (SHA-256 checked against Validation); the prediction intervals are the ones calibrated in Validation. Nothing was
refit, tuned or recalibrated after seeing these years. **2026 is excluded**: its data are incomplete (the year is not over
and CHIRPS rain is missing for 2026-10), and nothing was filled in.

Notebook: [`ml/notebooks/03_phase3_testing.ipynb`](../ml/notebooks/03_phase3_testing.ipynb). Tables:
`ml/artifacts/phase3_testing/`. **Final models (the standard models to use from now on): `ml/artifacts/final_model/`.**

## 1. Verdict

| | Soil water (28–100 cm) | NDVI |
|---|---|---|
| Accuracy and skill (criteria A–E) | **Pass** | **Pass** |
| 90 % interval coverage (criterion F) | **Fails**: 82 % instead of 87–93 % | **Fails**: 84 % instead of 87–93 % |

Both models keep beating the simple rules on new years, including the 2023 coastal El Niño. Their **error ranges are too
narrow**: a range sold as "90 %" contained the true value about 8 times in 10. Per the protocol nothing is changed after
Testing; the real coverage is written into the final package so the app can say it honestly (§5).

## 2. Data checks

- New NASA POWER files 2023–2025 (T2M, RH2M, WS2M, ALLSKY_SFC_SW_DWN): no `-999`, no duplicates, same grid as 1998–2017,
  dates 01/01/2023–12/31/2025, every test row joined.
- GEE tables: 2022 read as lag history only; 2023–2025 scored; 2026 not loaded. NDVI covers 2,296–2,585 of 2,585 cells per
  quarter. The wettest month of the period is **March 2023 (119 mm on average over the grid)**, the coastal El Niño.

## 3. Error metrics, 95 % confidence intervals

Block bootstrap: 1,000 resamples of 61 spatial blocks of 0.2° (≈ 22 km), each block carrying its 3 years.

**Soil water** (m³/m³, 112,536 rows, 3,126 cells) — baseline to beat: persistence (fixed in Validation)

| Metric | XGBoost | Persistence | Climatology |
|---|---|---|---|
| MAE | **0.0113** [0.0103, 0.0123] | 0.0227 | 0.0261 |
| RMSE | **0.0198** [0.0185, 0.0211] | 0.0367 | 0.0376 |
| R² | **0.962** [0.954, 0.968] | 0.868 | 0.861 |
| Bias (mean error) | **−0.0030** [−0.0036, −0.0024] | −0.0009 | −0.0127 |
| MAPE | **5.1 %** | — | — |
| RMSE skill vs persistence | **0.46** [0.44, 0.49] | | |

**NDVI** (index, 30,056 rows, 2,585 cells) — baseline to beat: climatology

| Metric | XGBoost | Climatology | Persistence |
|---|---|---|---|
| MAE | **0.094** [0.090, 0.097] | 0.119 | 0.129 |
| RMSE | **0.126** [0.121, 0.131] | 0.161 | 0.184 |
| R² | **0.53** [0.48, 0.57] | 0.23 | −0.01 |
| Bias | **−0.026** [−0.032, −0.020] | −0.083 | −0.003 |
| RMSE skill vs climatology | **0.21** [0.14, 0.29] | | |

(MAPE is not reported for NDVI: it crosses zero.)

**Across the three phases** (same models)

| | Training, internal 2016–2017 | Validation 2018–2022 | Testing 2023–2025 |
|---|---|---|---|
| Soil water RMSE · R² | 0.022 · 0.955 | 0.013 · 0.986 | 0.020 · 0.962 |
| Soil water skill vs persistence | 0.48 | 0.52 [0.48, 0.55] | 0.46 [0.44, 0.49] |
| NDVI RMSE · R² | 0.145 · 0.49 | 0.103 · 0.66 | 0.126 · 0.53 |
| NDVI skill vs climatology | 0.08 | 0.18 [0.10, 0.25] | 0.21 [0.14, 0.29] |

Error is larger in the years with a coastal El Niño (2017, 2023) and smaller in calm years; the skill over the simple
rules holds in all three phases.

**By year, province and season** (skill vs the baseline, 95 % CI)

| | Soil water | NDVI |
|---|---|---|
| 2023 · 2024 · 2025 | 0.49 · **0.20 [0.13, 0.28]** · 0.55 | 0.23 · 0.17 · 0.22 |
| Chiclayo · Ferreñafe · Lambayeque | 0.39 · 0.47 · 0.42 | 0.20 · **0.08 [−0.05, 0.16]** · 0.25 |
| Season | wet Jan–Apr 0.41 (RMSE 0.030) · dry 0.57 (RMSE 0.012) | Q1 0.21 · **Q2 0.12** · Q3 0.30 · Q4 0.33 |

Worst periods: soil water in **March 2023** (RMSE 0.053, bias −0.037: the model fills the soil less than the El Niño did);
NDVI in **Q2 2023** (RMSE 0.22, bias −0.15: it misses the greening after the El Niño rains).

## 4. Confidence: real coverage of the intervals

Widths fixed in Validation (split conformal, one width per season), checked here:

| Interval | Soil water: width (±) → coverage [95 % CI] | NDVI: width (±) → coverage [95 % CI] |
|---|---|---|
| "80 %" global | 0.011 → 70 % [67, 74] | 0.121 → 72 % [70, 74] |
| "90 %" global | 0.019 → **82 %** [80, 84] | 0.169 → **85 %** [83, 86] |
| "95 %" global | 0.029 → **89 %** [88, 90] | 0.219 → **92 %** [91, 93] |
| "90 %" by season (used by the app) | dry 0.013 → 84 % · wet 0.030 → 77 % | Q1 0.18 → 86 % · Q2 0.20 → 79 % · Q3 0.15 → 86 % · Q4 0.12 → 84 % |
| "90 %" by season, per year | 2023: 77 % · 2024: 84 % · 2025: 84 % | 2023: 81 % · 2024: 87 % · 2025: 84 % |

Reading: the intervals are honest about the size of a typical error but **overconfident by 6–8 points**, more in the rainy
season and in El Niño years. Coverage fell from Validation (87–88 %) to Testing (82–85 %), which matches errors that grow
when conditions move away from the training years (§6, risk 4).

## 5. Final models (the standard models)

`ml/artifacts/final_model/<model>/`:

| File | Content |
|---|---|
| `model.ubj` | The tested XGBoost model (identical to Phase 1) |
| `preprocessing.json` | Exact feature order, units, missing-value rule, training ranges for warnings |
| `intervals.json` | 90 % widths by season and global widths, calibrated on 2018–2022, **with their tested coverage** |
| `model_card.json` | Target, features, hyperparameters, seed, data, metrics with CIs per phase, intended use, what not to use it for |
| `baseline_climatology_*.parquet` | The baselines, to show next to the model |

Use from Python (the table must be built with `fs_ml.features`, as in every phase):

```python
from fs_ml.predict import load, predict
m = load("sm_root_monthly")          # or "ndvi_quarterly"
out = predict(m, table)              # prediction, low, high, out_of_range, far_out_of_range, unit
```

**How to present the intervals (team decision; the files stay as they are):**
- Option 1: show the "90 %" band and label it with what it really did: *"in 2023–2025 the true value fell inside this range
  about 8 times in 10"*.
- Option 2: show the wider "95 %" band (`half_width_global["95%"]`) with its real label: *"about 9 times in 10"* (89 % soil
  water, 92 % NDVI in Testing).

Never write "90 % confidence" without the measured coverage next to it.

**Standard parameters of the final models** (both `XGBRegressor`, `reg:squarederror`, `hist`, seed 42):

| | Soil water | NDVI |
|---|---|---|
| Trees (from early stopping) | 1,122 | 89 |
| `learning_rate` · `max_depth` · `min_child_weight` | 0.05 · 6 · 20 | 0.05 · 6 · 20 |
| `subsample` · `colsample_bytree` | 0.8 · 0.8 | 0.8 · 0.8 |
| `reg_alpha` · `reg_lambda` · `gamma` | 0 · 1 · 0 | 0 · 1 · 0 |
| Features | 19 | 16 |
| Training rows (1998–2017) | 750,240 | 91,224 |

## 6. Risks

1. **Overconfident intervals.** 90 % bands cover 82–85 %, and only 77 % in the rainy season of soil water and in 2023.
   Mitigation: label with the measured coverage (§5); recalibrate with each new year of data.
2. **Extreme rain is underestimated.** In March 2023 the soil water error is 2.7× the average and the model stays below
   the real peak; after El Niño rains the NDVI greening is missed (Q2 2023, bias −0.15). In an El Niño year, say so on screen.
3. **NDVI drifts low.** Bias −0.026, close to the 0.03 limit; the climatology is even lower (−0.083). Vegetation in
   2023–2025 is greener than in 1998–2017 (new irrigated land, such as Olmos, is a likely cause, not verified). Retrain when
   new years arrive, or the bias will grow.
4. **More inputs outside the training range.** Rows with any input outside the 1998–2017 p01–p99: 15–16 % in Validation,
   **18–21 % in Testing** (6-month rain, wind, temperature, evaporation). Error was not worse on them this time, but trees
   cannot extrapolate: a scenario beyond the hottest month seen gets the answer of the hottest month seen. The app must
   show the out-of-range warning.
5. **Weak spots:** NDVI in Ferreñafe (skill CI crosses 0 in Validation and Testing), NDVI in Q2, soil water in 2024 (skill
   0.20, just at the threshold).
6. **What the data cannot see:** ERA5-Land soil water ignores irrigation (Tinajones, Olmos, Motupe); values are ~9 km
   (soil, climate) and 2 km cells; NASA POWER points are 55–110 km apart. Not a measurement of a specific field.
7. **Not causal and not a forecast.** Changing an input shows the model's response, learned from 1998–2017; it does not
   prove a cause and does not predict a real future date.
8. **Out of scope:** no crop yield, crop type, rotation choice or risk class is predicted (no reference labels), and no VPD
   or GDD is derived.
9. **Data questions still open** (see `ML_PHASE1_TRAINING.md` §13): NDSI formula, NDVI sensor and mask, GAEZ legend and
   duplicates, the grid's region (37 % of cells fall outside Lambayeque), GAEZ license.

## 7. Notes on the protocol

- One evaluation of the frozen models. The notebook was executed a second time only to fix how the interval band is drawn;
  the code is deterministic, and the verdicts and tables did not change.
- A production model refit on 1998–2025 would use more data, but the numbers above would no longer describe it. For the
  hackathon the **tested** model is the standard model.
