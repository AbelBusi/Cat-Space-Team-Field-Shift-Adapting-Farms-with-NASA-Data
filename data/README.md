# Data folder

Everything the team needs for the hackathon, for the places in [`places.csv`](places.csv)
(5 Lambayeque spots + 5 example places on other continents). Add a row there to add a place.

## ✅ Already downloaded (open data, no login)

Refresh any time with `pipeline/.venv/bin/python pipeline/fetch_open_data.py` (or one source: `power`, `ndvi`, `soil`, `oni`).

| Folder / file | Source | What is inside |
|---|---|---|
| `power/<place>.json` | NASA POWER API, monthly 2001–2024 | `T2M`, `T2M_MAX`, `T2M_MIN`, `T2M_RANGE`, `PRECTOTCORR` (mm/day), `GWETTOP` / `GWETROOT` (soil wetness 0–1), `ALLSKY_SFC_SW_DWN`, `RH2M`, `WS2M`. Enough for heat, frost, rain, soil wetness and crop water demand (ET₀). Monthly `T2M_MAX`/`T2M_MIN` are the hottest/coldest **hour** of the month. |
| `ndvi/<place>.json` | MODIS MOD13Q1 v061 via ORNL DAAC | Plant greenness every 16 days in 2024, 250 m pixel |
| `soil/<place>.json` | ISRIC SoilGrids 2.0 | Clay, sand, silt, organic carbon, pH, bulk density, nitrogen at 0–5, 5–15 and 15–30 cm (mapped units: divide by `d_factor`) |
| `oni.txt` | NOAA Oceanic Niño Index | El Niño / La Niña by season, 1950 → today. **Aug–Oct 2026 = +2.46: a strong El Niño is happening now.** |

## 🔐 Needs a free Earthdata Login: a human must download these

An AI assistant cannot log in, and these portals hide the files behind the login (and some behind JavaScript),
so they cannot be scraped. Each one below has the most direct route. Save what you download in **`data/manual/<dataset>/`**
(big raw files there are git-ignored; small CSV/JSON results can be committed).

**Before anything:** create the account at <https://urs.earthdata.nasa.gov>. Then go to *Profile → Applications → Authorized Apps*
and approve **NASA GESDISC DATA ARCHIVE**, **LP DAAC Data Pool**, **PO.DAAC** and **NSIDC**. Without that, the downloads fail with 401.

Sizes checked in NASA's catalog (CMR) on Nov 13, 2026:

| # | Dataset | Why we want it | Raw size | Most viable route |
|---|---|---|---|---|
| 1 | **GRACE-FO groundwater** `TELLUS_GRAC-GRFO_MASCON_CRI_GRID_RL06.3_V4` | Underground water trend (the "Coming soon" signal) | **1 file, 40 MB** (Apr 2002 → Sep 2026) | **Script** (Route 0) |
| 2 | **NASADEM** `NASADEM_HGT` v001 (30 m) | Elevation and slope → erosion risk | ~12 MB per place | **Script** (Route 0) |
| 3 | **GPM IMERG monthly** `GPM_3IMERGM` V07 (0.1°) | Rain from space, El Niño floods, rain over the upper basin | 288 files, 5 GB (2001–2024) | **Script** (Route 0), or Route B to subset |
| 4 | **SMAP soil moisture** `SPL3SMP_E` v006 (9 km, daily) | Real soil moisture | **228 GB per year** | **AppEEARS points** (Route A) |
| 5 | **HLS NDVI** `HLSL30` / `HLSS30` v2.0, or `HLSL30_VI` (30 m) | Field-level greenness | millions of scenes | **AppEEARS points** (Route A) |
| 6 | **ECOSTRESS** `ECO_L2T_LSTE` v2 (LST) + `ECO_L3T_JET` v2 (ET), 70 m | Heat stress and water use of a plot | thousands of scenes | **AppEEARS points** (Route A) |

### ⛔ Do not download (checked: wrong product for this project)

- **SMAP CPEX** (`CPEX_SPEED_SMAP_...nc`): ocean **wind speed** from a 2017 hurricane campaign, 4°–21°N. Not soil moisture.
- **Kaggle "NASA anomaly detection SMAP-MSL"**: spacecraft telemetry for anomaly detection. Not Earth data.
- **`ECO_L4G_ESI_ALEXI`** (ECOSTRESS evaporative stress index): **covers only the USA (CONUS)**. Zero files over Peru.

Verified structure of what was downloaded, and the plan to display it fast: [`STRUCTURE.md`](STRUCTURE.md).
- **Any global daily product downloaded whole** (SMAP, HLS, IMERG daily): hundreds of GB. Use AppEEARS points or subsetting.

### Route 0 · Script for GRACE, NASADEM and IMERG (fastest)

1. Log in **once** in your terminal. It asks for your Earthdata username and password and saves them in `~/.netrc`:
   ```bash
   pipeline/.venv/bin/python -c "import earthaccess as ea; ea.login(strategy='interactive', persist=True)"
   ```
2. Run the script. Small tables appear in `data/grace/`, `data/terrain/` and `data/imerg/`. Raw files stay in `data/manual/` (git-ignored).
   ```bash
   pipeline/.venv/bin/python pipeline/fetch_earthdata.py grace dem     # ~2 min
   pipeline/.venv/bin/python pipeline/fetch_earthdata.py imerg         # 5 GB download, run it overnight
   ```

### Route A · AppEEARS, one request for SMAP, HLS and ECOSTRESS (all 10 places at once)

1. Open <https://appeears.earthdatacloud.nasa.gov> → *Sign In* → **Extract → Point Sample**.
2. *Start a new request* → name it `field-shift-points` → **Upload `data/places.csv`** (it already has the
   `ID,Category,Latitude,Longitude` format AppEEARS asks for).
3. Dates: **2019-01-01 to 2024-12-31** (ECOSTRESS starts mid-2018, SMAP in 2015).
4. Add these layers (type the product name in the search box):
   - `SPL3SMP_E.006` → `Soil_Moisture_Retrieval_Data_AM_soil_moisture`
   - `HLSL30.020` → `B04`, `B05`, `Fmask` and `HLSS30.020` → `B04`, `B8A`, `Fmask` (NDVI = (NIR − Red) / (NIR + Red))
   - `ECO_L2T_LSTE.002` → `LST` and `ECO_L3T_JET.002` → `ETdaily`
5. Output: **CSV**. Submit. You get an email when it is ready (minutes to a few hours, so **submit tonight**).
6. Download the CSVs into `data/manual/appeears/`.

If a product version or layer name is slightly different in the list, pick the newest version with the same short name and the closest layer name.

### Route B · GPM IMERG by hand, subset to Lambayeque (alternative to the 5 GB download)

1. <https://search.earthdata.nasa.gov> → search `GPM_3IMERGM` → choose **GPM IMERG Final Precipitation L3 1 month 0.1 degree V07**.
2. Draw a rectangle over **Lambayeque and its upper basin**: south −7.2, north −5.4, west −80.7, east −78.8.
3. Time: **2001-01-01 to 2024-12-31** → *Download all* → **Customize**: turn on *spatial subsetting* and choose **NetCDF4** output.
4. Choose *Download script*, save it in `data/manual/imerg/` and run it there (`sh download.sh`); it uses your Earthdata login.
5. The result is one small file per month (288 files). Variable `precipitation` is mm/hour; multiply by the hours in each month.

For one place only, **Giovanni** is faster: <https://giovanni.gsfc.nasa.gov> → *Time Series, Area-Averaged* → variable
`GPM_3IMERGM ... precipitation` → draw the box → *Plot Data* → *Download CSV*.

### Route C · GRACE-FO by hand (only if the script fails)

1. <https://search.earthdata.nasa.gov> → search `TELLUS_GRAC-GRFO_MASCON_CRI_GRID_RL06.3_V4`.
2. It is **one global NetCDF file** covering 2002 → today. Download it into `data/manual/grace/`.
3. Variable `lwe_thickness` (cm of water) on a 0.5° grid. The trend per cell is the slope of a straight line over time.
   That small table is what the app needs for "Underground water".

Or, with Python after logging in once (`earthaccess` saves the login in `~/.netrc`):

```bash
pipeline/.venv/bin/python -c "import earthaccess as ea; ea.login(persist=True); ea.download(ea.search_data(short_name='TELLUS_GRAC-GRFO_MASCON_CRI_GRID_RL06.3_V4'), 'data/manual/grace')"
```

## What not to try

- **Worldview, Giovanni and Earthdata Search pages** are JavaScript apps: scraping them does not work. Use the routes above.
- **Full global daily files** (IMERG daily, SMAP L4) are gigabytes. Always subset to the area first.
