# Field Shift ML · Phase 2 checks for the API expansion

Status (Nov 15, 2026): **checks run (notebook `ml/notebooks/07_api_validation.ipynb`, rules committed before in `6ccc253`). 3 pass, 5 fail, 1 not testable, 1 deferred.** They decide which new API features may be served without
the `experimental` label (`ml-api/roadmap/README.md`, Phase 2). The tested models are not changed or retrained.
Results will go to `ml/artifacts/api_validation/checks.json`, which the API reads at startup.

## Common setup

- Models: the tested v1 models (`ml/artifacts/final_model/`). Engine: `ml/fs_ml/project.py`, as in the app.
- Starts: the end of every month from Dec 2017 to Dec 2021 (49 starts) for scenario checks; Dec 2017 – Nov 2022 for
  hindcast-type checks. Analog years 1998–2017, never a month after Dec 2017 (as in `ML_PROJECTIONS.md`).
- Cells: the 1,950 Lambayeque cells with soil water, except check S8.
- **Tolerance.** The first scenario checks (`ML_PROJECTIONS.md` §4.3) counted any move above 1e-4 m³/m³ as "wrong
  direction"; both failed. Those results stand. The checks below ask a different question, written now and knowing
  that result: *does a scenario move soil water in the wrong direction by more than the model's own error*
  (validation RMSE **0.0125 m³/m³**)? The strict 1e-4 count is also reported.

## Checks

| # | Feature | Rule (all must hold to pass) |
|---|---|---|
| S1 | Temperature what-if | With +2 °C in every month (horizon 3), the median soil water at lead 3 rises above the normal year by more than 0.0125 in ≤ 1 % of cells (more heat must not make the soil clearly wetter). Same for −2 °C falling by more than 0.0125. |
| S2 | Droughts of 1–6 months | Dry months 1…n (n = 1…6), horizon 6: (i) the mean change at the end of the drought is negative for every n; (ii) the mean change at lead 6 does not rise with n by more than 0.001 (longer droughts are not wetter); (iii) at the end of the drought ≤ 1 % of cells rise by more than 0.0125. |
| S3 | Rain-only what-if | Horizon 3: rain × 0.5 raises lead-3 soil water by more than 0.0125 in ≤ 1 % of cells, rain × 2 lowers it by more than 0.0125 in ≤ 1 %, **and** the mean effect has the right sign and at least a quarter of the model error (0.003) in size. |
| S4 | Recovery after a drought | Dry months 1–3, horizon 12: the difference with the normal year at lead 12 is smaller in size than at lead 3 in ≥ 90 % of cells (the model "forgets" the drought). This tests the model's behaviour, not real soil recovery. |
| S5 | Drought risk (share of analog members below the cell's 20th percentile for that month, 1998–2017) | Hindcasts, leads 1–3: in each of 5 equal-width bins of the predicted share with ≥ 1,000 cases, the observed frequency differs from the mean predicted share by ≤ 0.10, and the Brier skill score against the constant 0.20 is > 0. |
| S6 | Alerts (observed value below the lower end of the lead-1 90 % band) | Hindcast months 2018–2022: the share of cells flagged is between 2.5 % and 10 % (5 % expected), for soil water (monthly) and NDVI (quarterly). |
| S7 | NDVI "greener than expected" (possible irrigation) | No independent irrigated-area data in the repository: **cannot be validated**. Only descriptive results; stays experimental. |
| S8 | The 1,176 grid cells outside Lambayeque | Same tables and code as Phase 2, only those cells, Validation 2018–2022: criteria A–E of `ML_PHASE1_TRAINING.md` §10 with the same thresholds (95 % CI by 0.2° block bootstrap). Testing 2023–2025 reported only. |
| S9 | Adaptive ranges (CQR + monthly recalibration) | Needs complete 2026 data: **deferred**, not run. |
| S10 | Per-cell confidence (historical error of a cell) | Per ERA5-Land pixel group (cells sharing the same 0.1° pixel), the Spearman correlation between the validation RMSE (2018–2022) and the testing RMSE (2023–2025) is ≥ 0.5 for soil water (the past error of a place tells something about its future error). |

## How the API uses the results

- Pass → the feature is served with level `ok` or `warning` (depending on the inputs, as always).
- Fail, deferred or not testable → served only with level `experimental` and the reason.
- Nothing is tuned after seeing the results; a failed check is reported, not fixed by hand.

## Results

| # | Feature | Result | Numbers |
|---|---|---|---|
| S1 | Temperature what-if | **Fail** | +2 °C makes soil water *rise* by more than the model error in 9.7 % of cells (mean +0.0024 m³/m³, the wrong way); −2 °C falls in 0.6 %. With the strict 1e-4 count, 55 % rise |
| S2 | Droughts of 1–6 months | **Fail** | Mean change at the end of the drought is negative for every length (−0.002, −0.012, −0.017, −0.020, −0.022, −0.023 m³/m³) and longer droughts are drier at lead 6; but cells rising by more than the model error reach 1.4 % (5 months) and 2.5 % (6 months), above 1 %. Lengths 1–4 meet all three parts |
| S3 | Rain-only what-if | **Fail** | Wrong-way moves are rare (0.15 % / 0.46 %), but the mean effect is only −0.0006 (× 0.5) and +0.0006 (× 2) m³/m³, a twentieth of the model error |
| S4 | Recovery after 3 dry months | **Fail** | The difference shrinks by lead 12 in 83 % of cells (needed 90 %); mean −0.017 at lead 3, −0.0015 at lead 12 |
| S5 | Drought risk | **Fail** | Overconfident: predicted 0.95 → observed 0.65; predicted 0.68 → 0.35 (max gap 0.34). Still better than a constant 0.20 (Brier skill 0.18) |
| S6 | Alerts | **Pass** | 4.7 % of cells flagged for soil water, 3.7 % for NDVI (5 % expected) |
| S7 | NDVI greener than expected | Not testable | 591 cells (23 %) were above the model by more than its error in ≥ 3 of the 8 quarters of 2024–2025; no irrigated-area data to check them |
| S8 | Cells outside Lambayeque | **Pass** | Soil water skill 0.54 [0.50, 0.58] vs climatology, RMSE 0.014, worst year 0.48; NDVI skill 0.12 [0.05, 0.18], worst year 0.04. Testing 2023–2025 (report): 0.42 and 0.17 |
| S9 | Adaptive ranges | Deferred | needs complete 2026 data |
| S10 | Per-cell confidence | **Pass** | Spearman 0.65 between validation and testing RMSE over 226 ERA5-Land pixel groups |

**What the API does with them:** alerts, per-cell confidence and the cells outside Lambayeque are served as validated
(level `warning`, never `ok`, because they are still model outputs with known limits). Temperature, droughts, rainfall,
recovery, drought risk, NDVI anomalies and hotspots are served with level `experimental` and the reason. El Niño
analogs and a normal year are not scenario *changes* and keep their own warnings (few analogs, beyond the useful lead).

**Reading:** the model's response to changed weather is dominated by last month's soil water; changes of one input at a
time move it little and sometimes the wrong way. Simulations that change inputs need a model that reacts to them
(ERA5-Land's own rain, monotone constraints): Phase 3.
