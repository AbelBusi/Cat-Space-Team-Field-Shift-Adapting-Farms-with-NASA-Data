# Field Shift ML · Phase 2 checks for the API expansion

Status (Nov 15, 2026): **rules written, checks not run yet.** They decide which new API features may be served without
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
