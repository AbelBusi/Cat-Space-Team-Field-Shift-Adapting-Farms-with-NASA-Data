# Field Shift ML · Trends 1998–2025 and their extension to 2030

Status (Nov 15, 2026): **rules written before the check was run** (this section must not be edited after seeing results).
Results go to §3 and to `ml/artifacts/trends/trend_check.json`.

## 1. Why this is not a model projection

The team asked for "trends to 2030" in the "What's ahead" track. The analog-ensemble projections of the models are
useful only for the first 6 months (`ML_PROJECTIONS.md`, `ML_V3_ERA5_RAIN.md`); run further, they return a typical
year again and again. So the years 2027–2030 are **not** model output. They are the observed trend of each place,
extended, with the year-to-year range around it, and labelled "if the trend of 1998–2025 continues".

## 2. Rules

**Data** (per 2 km cell inside Lambayeque, from the API cube, the same data the app shows):

| Variable | Yearly value | Source |
|---|---|---|
| Deep soil water (28–100 cm) | mean of the 12 months (year needs all 12) | ERA5-Land |
| 2 m temperature | mean of the 12 months | ERA5-Land |
| Rain | sum of the 12 months | CHIRPS |
| Greenness (NDVI) | mean of the quarters with an image (year needs ≥ 3) | team's GEE composite |

**Trend.** Theil–Sen slope of the yearly values against the year (median of all pairwise slopes; robust to single
El Niño years), with its 95 % interval by Sen's method (normal approximation of Kendall's S). A trend is called
**clear** only if that interval excludes zero; otherwise the app says "no clear trend".

**Extension to 2030.** Centre: the Theil–Sen line. Range: the line ± the 5–95 % of the cell's own detrended yearly
values (year-to-year variation, El Niño included), plus the spread of the slope's interval at that year. Shown as a
dashed line and a band, never as a number for a single year without its range.

**Check T (decides how the extension is labelled).** For each variable and every Lambayeque cell: fit the trend on
1998–2017 only, extend it to the yearly values of 2018–2025, and compare with "no change" (the 1998–2017 median).
RMSE skill of trend over no change, with a 95 % CI by the same 0.2° spatial block bootstrap as every phase (1,000
resamples, seed 42).

| Result | What the app says next to the 2027–2030 extension |
|---|---|
| Lower CI of the skill > 0 | "In tests on 2018–2025, extending the trend was closer to reality than assuming no change." |
| Otherwise | "In tests on 2018–2025, extending the trend was not better than assuming no change: read it as a direction, not a number." |

Nothing is tuned after the check. 2026 is not used (incomplete).
