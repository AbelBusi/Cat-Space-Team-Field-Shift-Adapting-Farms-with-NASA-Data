# Data sources

Ranked by how useful each source is for the Field Shift goal: **helping a farmer compare crop rotations
for soil health and for resilience to heat, water shortage and extreme rain.**

> **Status today (Nov 11, 2026):** the app works **anywhere on Earth**. It fetches NASA POWER and MODIS NDVI live for the
> grid cell under the chosen point. Rotation scores and the confidence meter are still hypothetical.
> The challenge's Resources tab opens on **Nov 13**. Re-check this ranking against it.

Space Apps rules: **cite every source** in the submission form (NASA's too), and use non-NASA material only
if it is free and openly licensed. The "Cite as" lines below are ready to paste.

## Access tiers

| Tier | Meaning | How we get it |
|---|---|---|
| **A · Live** | No login. Works for any point on Earth. | Straight from the browser or a Python script. |
| **B · Login** | Free [Earthdata Login](https://urs.earthdata.nasa.gov) needed. | A team member logs in once. `earthaccess` (Python) downloads them, and we save small global grids (for example 0.5°, one value per cell) in `web/public/data/` for the app to read. |
| **C · Reference** | Tables and papers. | Typed into the pipeline by hand, with the citation. |

An AI assistant can write the scripts, but it cannot log in for you. A **human** creates the Earthdata account and runs
the tier B scripts. For GPM, open your Earthdata profile → *Applications → Authorized Apps* and approve
**"NASA GESDISC DATA ARCHIVE"**, or the downloads fail with 401.

## Ranking

| # | Source | What it tells the farmer | Pixel size | Tier | Status in app |
|---|---|---|---|---|---|
| 1 | **NASA POWER** | Daily/monthly heat, frost, rain, sun, humidity, wind. These are also the inputs for crop water demand (ET₀). | 0.5° × 0.625° (~55 km) | A | ✅ **Live in app**: heat, rain, soil wetness (`GWETTOP`), frost |
| 2 | **HLS: Landsat 8/9 + Sentinel-2** (NDVI) | Which months the field is bare, when crops peak, which plots are stressed. | 30 m | B | Drawn as a grid cell; data planned |
| 3 | **GPM IMERG** | Monthly rain, extreme-rain days, El Niño floods. Rain over the upper basin feeds the reservoir. | 0.1° (~11 km) | B | Drawn as a grid cell; data planned (POWER rain is used meanwhile) |
| 4 | **MODIS via ORNL DAAC subsets** (NDVI, ET, LST) | Same idea as #2, coarser, but needs **no login**, so it is the quick global fallback. | 250 m–1 km | A | ✅ **Live in app**: NDVI 2024 (slow, ~40–60 s, cached) |
| 5 | **ISRIC SoilGrids** | Texture (sand/silt/clay), organic carbon, pH. Organic matter and infiltration depend on these. | 250 m | A | Not used yet |
| 6 | **SMAP** soil moisture | Dry-soil months and moisture anomalies. | 9–36 km | B | Drawn as a grid cell; data planned |
| 7 | **ECOSTRESS** (LST, ET) | Midday heat stress and real evapotranspiration of a plot. | 70 m, irregular dates | B | Mentioned in evidence text |
| 8 | **SRTM / NASADEM** elevation | Slope → erosion risk when the soil is bare. | 30 m | B | Not used yet |
| 9 | **GRACE / GRACE-FO** | Long-term trend of underground water. Regional context only. | ~300 km | B | Shown as "coming soon" |
| 10 | **FAO-56 crop coefficients (Kc)** | Crop water use: `ETc = Kc × ET₀` per growth stage. The core of the "save water" score. | — | C | Not used yet (scores are hypothetical) |
| 11 | **NOAA Oceanic Niño Index (ONI)** | Which past years were El Niño or La Niña, so the app can show "a year like 2017". | — | A | ✅ Its El Niño years define the "El Niño years" view |
| 12 | **Local data** (for the Peru demo: MIDAGRI crop calendars, ANA / Tinajones water allocations) | Local planting seasons, how much water a farm gets. | — | C | Not used yet |

### Tools to explore before coding (no code needed)

- **[Worldview](https://worldview.earthdata.nasa.gov)**: browse daily satellite imagery. Good for screenshots of the 2017 coastal El Niño.
- **[NASA GIBS](https://nasa-gibs.github.io/gibs-api-docs/)**: the same imagery as map tiles (WMTS, no login). ✅ The app's map uses `BlueMarble_ShadedRelief_Bathymetry` and `Reference_Labels_15m`.
- **[AppEEARS](https://appeears.earthdatacloud.nasa.gov)**: point or polygon extraction for HLS, MODIS, SMAP, ECOSTRESS and SRTM, exported as CSV. Login required. The easiest way to get tier B data without writing much code.
- **[Giovanni](https://giovanni.gsfc.nasa.gov)**: quick time-series plots of GPM and other variables. Login required.
- **[Earthdata Search](https://search.earthdata.nasa.gov)**: find any product by name and area.

## Details per source

### 1. NASA POWER — Prediction Of Worldwide Energy Resources
- **API:** `https://power.larc.nasa.gov/api/temporal/{daily|monthly|climatology}/point?parameters=...&community=AG&latitude=..&longitude=..&format=JSON`
- **In the app (monthly endpoint, 2001–2024):** `T2M` + `T2M_RANGE` (typical afternoon high = `T2M + T2M_RANGE/2`), `T2M_MIN` (frost),
  `PRECTOTCORR` (rain, mm/day × days in month) and `GWETTOP` (topsoil wetness, 0–1, shown as %).
- **Watch out:** in the monthly and climatology endpoints, `T2M_MAX` / `T2M_MIN` are the single hottest / coldest **hour** of the
  period, not the average daily high / low. In Iowa in March, `T2M_MAX` averages 21.6 °C, while the typical high is about 9 °C.
- **For crop water demand (ET₀), later:** also `ALLSKY_SFC_SW_DWN` (sun), `RH2M` and `WS2M`.
- **Checked Nov 11, 2026:** answers without a key in about 1 s and sends `Access-Control-Allow-Origin: *`, so the Vue app calls it directly.
- **Real samples (typical year):** Chiclayo, Peru: 93 mm of rain a year. Iowa, USA: 840 mm a year and 7 frost-risk months. Punjab, India: 715 mm a year and 8 months with afternoon highs of 30 °C or more.
- **Cite as:** "These data were obtained from the NASA Langley Research Center (LaRC) POWER Project funded through the NASA Earth Science/Applied Science Program." Also add the API version from the response header (it was v2.10.1).

### 2. HLS — Harmonized Landsat Sentinel-2
- **Products:** `HLSL30` (Landsat) and `HLSS30` (Sentinel-2), version 2.0, from LP DAAC. Compute `NDVI = (NIR − Red) / (NIR + Red)` and mask clouds with the `Fmask` band.
- **Cite as:** NASA LP DAAC, HLSL30 v2.0, doi:10.5067/HLS/HLSL30.002 and HLSS30 v2.0, doi:10.5067/HLS/HLSS30.002.

### 3. GPM IMERG
- **Products:** `GPM_3IMERGDF` (daily, Final run, V07) or `GPM_3IMERGM` (monthly). From GES DISC.
- **Cite as:** Huffman, G.J. et al., GPM IMERG Final Precipitation L3 1 day 0.1° V07, GES DISC, doi:10.5067/GPM/IMERGDF/DAY/07.

### 4. MODIS through the ORNL DAAC subset service
- **API:** `https://modis.ornl.gov/rst/api/v1/` (no login, allows browser calls). Products: `MOD13Q1` (NDVI, 250 m, 16 days), `MOD16A2GF` (ET), `MOD11A2` (LST).
- **Limits found:** at most 10 images per request, and each request took about 40 s. The app sends 3 requests in parallel for 2024 and caches the result in the browser. For the demo, open the example places once beforehand.
- **Cite as:** Didan, K., MOD13Q1 v061, NASA LP DAAC, doi:10.5067/MODIS/MOD13Q1.061, plus "ORNL DAAC MODIS and VIIRS Land Products Global Subsetting and Visualization Tool".

### 5. ISRIC SoilGrids
- **API:** `https://rest.isric.org/soilgrids/v2.0/properties/query?lon=..&lat=..&property=clay&property=soc&depth=0-5cm&value=mean`. It has been slow or down at times, so cache the answers.
- **License:** CC-BY 4.0 (third-party, allowed with attribution).
- **Cite as:** Poggio, L. et al. (2021), SoilGrids 2.0, SOIL 7, 217–240, doi:10.5194/soil-7-217-2021.

### 6. SMAP
- **Products:** `SPL3SMP_E` (L3, 9 km, daily) or `SPL4SMGP` (L4 surface and root-zone moisture). From NSIDC DAAC.
- **Caution:** on irrigated coast the 9 km pixel mixes desert, fields and city. Present it as "the area", never as "your field".
- **Cite as:** copy the DOI from the product's NSIDC page.

### 7. ECOSTRESS
- **Products:** Collection 2 tiled LST (`ECO_L2T_LSTE`) and ET (`ECO_L3T_JET`) from LP DAAC. Overpass times vary because it flies on the ISS.
- **Cite as:** copy the DOI from the LP DAAC page.

### 8. SRTM / NASADEM
- **Products:** `SRTMGL1` v003 or `NASADEM_HGT`. Compute slope in degrees.
- **Cite as:** NASA JPL (2013), SRTMGL1 v003, NASA LP DAAC, doi:10.5067/MEaSUREs/SRTM/SRTMGL1.003.

### 9. GRACE / GRACE-FO
- **Product:** JPL mascon terrestrial water storage (RL06.x), from PO.DAAC or GRACE Tellus.
- **Caution:** one pixel covers a large part of northern Peru. Say "regional trend", never "your well".
- **Cite as:** copy the DOI from the PO.DAAC page.

### 10. FAO-56 crop coefficients
- Allen, R.G., Pereira, L.S., Raes, D., Smith, M. (1998). *Crop evapotranspiration — Guidelines for computing crop water requirements*. FAO Irrigation and Drainage Paper 56. Use Table 12 (Kc) and Table 11 (stage lengths), and cite the paper.

### 11. NOAA ONI
- `https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/ensostuff/ONI_v5.php`. US government data, public domain.

### 12. Local data (Peru demo)
- **Crop calendars and statistics:** MIDAGRI. **Water allocation:** ANA and the Tinajones project operator. Ask local agronomists. This is the "local expertise" the challenge mentions.

### 13. Training data of the XGBoost models (Phase 1, `ml/`)
Exported by the team from Google Earth Engine and other portals (folder *Datos para proyecto Nasa*). Details and irregularities:
`docs/ML_PHASE1_TRAINING.md`.
| Source | Variables | Grid | License / cite |
|---|---|---|---|
| **CHIRPS** (UCSB Climate Hazards Center) | Monthly rain | ~5.5 km | Public domain-like open data. Funk et al. (2015), doi:10.1038/sdata.2015.66 |
| **ERA5-Land** (ECMWF / Copernicus) | 2 m temperature, potential evaporation, soil water layers 1 (0–7 cm) and 3 (28–100 cm) | ~9 km | Copernicus licence (free, attribution). Muñoz-Sabater et al. (2021), doi:10.5194/essd-13-4349-2021 |
| Quarterly **NDVI / NDSI** composite (sensor not documented, probably Landsat: NASA/USGS public domain) | NDVI | 2 km cells | To confirm with the exporter |
| **NASA POWER** regional monthly (MERRA-2, CERES) | RH2M, WS2M, ALLSKY_SFC_SW_DWN (T2M kept, not used) | 0.5° × 0.625° / 1° | NASA open data |
| **FAO GAEZ v4** soil qualities | Nutrient, oxygen, lime/gypsum, salinity/sodicity, rooting classes | 5′ (~9 km) | ⚠️ As far as we know CC BY-NC-SA 3.0 IGO (non-commercial): confirm with the Local Lead. Fischer et al. (2021), doi:10.4060/cb4744en |

### Map imagery and place search (third-party, check before submission)
| Source | Use in the app | License / terms |
|---|---|---|
| **Sentinel-2 cloudless 2024** by EOX (s2maps.eu) | Satellite base map up to zoom 14 | ⚠️ CC BY-NC-SA 4.0 (non-commercial, share-alike). Not an OSI license: confirm with the Local Lead, or switch to NASA GIBS imagery for the submission |
| **Esri World Imagery** | Detailed base map from zoom 12 to 17 | ⚠️ Esri terms of use (not open). Same check as above |
| **OpenStreetMap Nominatim** | Place-name search | Data © OpenStreetMap contributors, ODbL. Usage policy: light use, cache results, show attribution |
| **NASA GIBS** `MODIS_Terra_NDVI_8Day`, `MODIS_Terra_Land_Surface_Temp_Day`, `IMERG_Precipitation_Rate`, `SMAP_L3_Passive_Enhanced_Day_Soil_Moisture` | Optional NASA image layers over the photo | NASA open data |
| **OpenStreetMap** administrative boundaries (admin levels 4, 6, 8) | Lambayeque, its 3 provinces and 38 districts (`web/src/data/lambayeque_admin.json`, `pipeline/build_districts.py`) | © OpenStreetMap contributors, **ODbL**: attribution shown on the map and in the report |
| **Terrain Tiles** on AWS Open Data (Terrarium PNG) | Heights for the 3D view of an outlined field. In Peru the tiles come from **NASA SRTM** (30 m), as the tiles' `x-imagery-sources` header says | Open data; SRTM is NASA/USGS public domain. Credit shown in the 3D view |
| **OpenStreetMap** place nodes (city, town, suburb, village, hamlet) | 650 town and village names on the map (`web/src/data/lambayeque_places.json`, `pipeline/build_places.py`) | © OpenStreetMap contributors, **ODbL** |

### Partner agencies (allowed and optional)
- **ESA Copernicus Sentinel-2** (dataspace.copernicus.eu): raw Sentinel-2. HLS already includes it, so we only need it if HLS fails.
- **JAXA GSMaP** (G-Portal): alternative rainfall product.

## Software and fonts used (licenses for the submission)

| Package | Use | License |
|---|---|---|
| Vue 3 | UI | MIT |
| Vite, @vitejs/plugin-vue | dev server and build | MIT |
| D3 | scales, shapes, colors | ISC |
| Leaflet | world map | BSD-2-Clause |
| Tailwind CSS | layout and responsive classes | MIT |
| three.js | 3D view of the outlined field (loaded only when it opens) | MIT |
| @fontsource packages | self-hosted fonts | MIT (package), fonts below |
| Atkinson Hyperlegible, Bricolage Grotesque, Pixelify Sans | type | SIL Open Font License 1.1 |
| earthaccess | Earthdata login and downloads | MIT |
| xarray | gridded data | Apache-2.0 |
| h5netcdf, pandas, NumPy, scikit-learn | file reading and analysis | BSD-3-Clause |

The cat "Sprout" and its sprites are original, created for this project and drawn in code (`web/src/cat/sprites.js`).
No meme images or game assets are used.
