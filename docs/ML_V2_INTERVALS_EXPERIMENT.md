# Field Shift ML · Experiment v2: fixing the error ranges

Status (Nov 15, 2026): **experiment, not adopted.** Nothing from Phases 1–3 was modified: the tested v1 models and
`ml/artifacts/final_model/` are untouched. Notebook: [`ml/notebooks/04_v2_intervals_experiment.ipynb`](../ml/notebooks/04_v2_intervals_experiment.ipynb);
outputs: `ml/artifacts/v2_intervals_experiment/`.

**Caveat:** 2023–2025 was already used by the Phase 3 test, so the numbers below are a *second look*, not an independent
test. Every choice in this experiment (method variant, γ) was made on Validation 2018–2022 only; the clean confirmation
will be 2026 once its data are complete.

## 1. Diagnosis: is it overfitting?

| | In-sample 1998–2017 | Validation 2018–2022 | Testing 2023–2025 |
|---|---|---|---|
| Soil water RMSE (m³/m³) | 0.007 | 0.013 | 0.020 |
| NDVI RMSE | 0.101 | 0.103 | 0.126 |

- **Mild overfitting, stable generalization.** The soil water model fits its own years 2–3× better than new years (normal for
  boosted trees), but its skill over the simple rule is the same in every phase (0.48 / 0.52 / 0.46). More regularization
  would shrink the in-sample number, not the error on new years. NDVI barely overfits at all.
- **The real causes of the failed ranges:**
  1. **Error grows with rain, the v1 range does not.** Soil water error in months of 30–60 mm is 2–3.5× the error of dry
     months, and the v1 range (one width per season) covered only 71 % of those months in 2023–2025.
  2. **Drift.** In 2023–2025 the error doubled even in months without rain (0.004 → 0.009 m³/m³). Conditions moved away
     from the past (warmer months, greener valleys, 18–21 % of inputs outside the training range): no width fixed in the
     past can promise 90 % under drift.
  3. **El Niño is not in the inputs.** In March 2023 the model stays below the real soil water peak, and in Q2 2023 below
     the NDVI greening. Nothing in the features tells it "this is a coastal El Niño".

## 2. What was tried (no new data needed)

1. **CQR — conformalized quantile regression** (Romano et al., 2019): two XGBoost models for the 5 % and 95 % quantiles,
   trained on 1998–2017 (which includes the El Niño years 1998 and 2017) with the same features and settings as v1, and
   corrected on Validation. The range widens by itself in the months that were hard in the past.
2. **Monthly recalibration — adaptive conformal inference** (Gibbs & Candès, 2021): each month the width is recomputed
   from the errors of the last 3 years already observed (same season), and the level rises after a month that missed too
   often (step γ, chosen on Validation: 0.2). In the app this means: when a new month of data arrives, update the width.

## 3. Results on 2023–2025 (90 % nominal)

| Range | Soil water: coverage [95 % CI] · mean width | NDVI: coverage [95 % CI] · mean width | Interval score (soil · NDVI, lower = better) |
|---|---|---|---|
| v1 (tested) | 82 % [79, 84] · 0.037 | 84 % [83, 85] · 0.33 | 0.102 · 0.56 |
| v2 CQR | 82 % [81, 84] · 0.039 | 86 % [84, 87] · 0.35 | 0.082 · 0.50 |
| v1 + monthly recalibration | 90 % [89, 92] · 0.063 | 87 % [86, 88] · 0.36 | 0.097 · 0.56 |
| **v2 CQR + monthly recalibration** | **90 % [89, 91] · 0.051** | **89 % [88, 90] · 0.39** | **0.081 · 0.49** |

- **CQR + monthly recalibration reaches the promised 90 %** in both models, passes rule F (87–93 %) and has the best
  interval score (Gneiting & Raftery, 2007), which rewards narrow ranges and punishes misses.
- By year: soil water 89 % · 90 % · 92 % (2023 · 2024 · 2025); NDVI 88 % · 93 % · 86 %. By season: rainy months of soil
  water 77 % → 89 %; NDVI Q2 79 % → 85 %.
- The price is honesty in width: soil water ranges are on average ± 0.026 m³/m³ instead of ± 0.018.
- **Still not solved: single extreme months.** In March 2023 and May 2024 only about half of the cells fell inside the
  range (`v2_aci_coverage.png`). Recalibration fixes the average, not the month of the shock: that needs information the
  model does not have (§4).

**Recommendation:** adopt *CQR + monthly recalibration* as the error range of the app **after the team agrees**, as a new
`final_model_v2` (the v1 package stays as it is), and confirm it on complete 2026 data. The point predictions do not
change.

## 4. What needs new data (please send)

| # | Data | Why | Where |
|---|---|---|---|
| 1 | **Niño 1+2 SST anomaly, monthly 1998–2025** (or ENFEN's ICEN) | Tells the model a coastal El Niño is happening; aimed at the March 2023 type of miss | NOAA CPC `sstoi.indices` (public domain) or ENFEN/IGP Peru |
| 2 | **ERA5-Land `total_precipitation_sum`** monthly, same GEE export and grid, 1998–2025 (and `volumetric_soil_water_layer_2` if possible) | The soil water target comes from ERA5-Land, which is driven by its own rain, not CHIRPS; the mismatch hurts in storm months | Same GEE script, `ECMWF/ERA5_LAND/MONTHLY_AGGR` |
| 3 | **Land cover or irrigated area per year** (e.g. MapBiomas Perú annual collection, the Olmos project's irrigated area by year, Tinajones monthly releases) | Explains the NDVI drift (greener valleys) that the weather cannot | MapBiomas Perú, PEOT / Olmos project, ANA |
| 4 | **2026, once complete** | Independent confirmation of v2 | Same files as before |
| 5 | Optional: **SMAP soil moisture 2015–2025** | Checks ERA5-Land soil water against an observation | NASA Earthdata (SPL3SMP_E) |

With 1–3, the point models would be retrained as **v2 models** following the same three phases (train 1998–2017, validate
2018–2022), and judged against v1 with the same rules; v1 stays as the reference.

## References

- Romano, Y., Patterson, E., Candès, E. (2019). Conformalized quantile regression. *NeurIPS 32*.
- Gibbs, I., Candès, E. (2021). Adaptive conformal inference under distribution shift. *NeurIPS 34*.
- Gneiting, T., Raftery, A.E. (2007). Strictly proper scoring rules, prediction, and estimation. *JASA* 102(477), 359–378.
