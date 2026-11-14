# Official challenge resources: what we have, what works by API, what does not

The challenge's Resources tab lists 25 sources. Each one was checked on Nov 14, 2026 against real endpoints
(HTTP status and whether a browser page may call it, i.e. CORS). Goal of the app: **any place on Earth**, with
Lambayeque (Peru) as the demo, and Iowa (USA) as a second example.

**Key finding:** 13 of the 25 sources cover **only the United States**. They are useful for the Iowa example (a
"US detail" bonus), not for Peru or a global tool.

## Summary

| Status | Sources |
|---|---|
| ✅ **In the app now** | NASA POWER (live), MODIS NDVI via ORNL (live), NASA GIBS imagery (live), GPM IMERG monthly (downloaded, Lambayeque), SRTM/NASADEM (downloaded), GRACE-FO (downloaded, not in the list but NASA) |
| ⚡ **Live API, no login, works from the browser: add next** | GIBS **IMERG** and **SMAP** image layers, USDA **SSURGO** soil (US), **CoCoRaHS** rain (US/Canada) |
| 🔑 **Needs a free account or key: precompute with Python, not live** | SMAP data, ECOSTRESS, Landsat/HLS, VIIRS, GLDAS/NLDAS, GEDI, Sentinel-2, ERA5, NASS QuickStats, OpenET, AMS Market News |
| 🖐 **Manual download from a website** | **FAO GAEZ** (global crop suitability, the most valuable missing piece), PRISM, NLCD, NAIP, LANDFIRE, Web Soil Survey, Ag Data Commons |

## Source by source

Usefulness: ★★★ core for our goal · ★★ helps · ★ nice to have · — not for us.

### NASA data

| Source | Use | Coverage | Access (tested) | Verdict |
|---|---|---|---|---|
| **NASA POWER** | ★★★ climate, frost, heat, ET₀ inputs | Global | ✅ No login, CORS `*`, ~1 s | **In the app.** Keep as the backbone |
| **GPM IMERG** | ★★★ rain, extremes, El Niño | Global | Data: Earthdata login. Images: ✅ GIBS layer `IMERG_Precipitation_Rate` works with CORS | Downloaded for Lambayeque (288 months). **Add the GIBS layer to the map** |
| **SMAP** | ★★★ real soil moisture | Global (9–36 km) | Data: Earthdata login (raw = 228 GB/yr). Images: ✅ GIBS `SMAP_L3_Passive_Enhanced_Day_Soil_Moisture` works | Harmony subset already ordered (job `46f7d1a1…`). **Add the GIBS layer now**; numbers from the subset or AppEEARS |
| **Landsat / HLS** | ★★★ field-level NDVI, bare months | Global (30 m) | Earthdata login; AppEEARS task already ordered | Precompute per place (AppEEARS points) |
| **MODIS** | ★★★ NDVI 250 m | Global | ✅ ORNL DAAC REST, no login, CORS | **In the app.** ⚠️ Slow (~40 s) and **was down (HTTP 503) during this check** → rely on the browser cache |
| **VIIRS** | ★★ MODIS successor | Global | ORNL `VNP13A1` same API, but 503 during the check; else Earthdata login | Swap in when MODIS ends; same code path |
| **SRTM / NASADEM** | ★★ slope, erosion risk | Global (60°N–56°S) | Earthdata login | Downloaded for Lambayeque (8 tiles). Precompute slope per place |
| **ECOSTRESS** | ★★ heat stress, real ET, 70 m | Global, irregular dates | Earthdata login; AppEEARS task already ordered | Precompute monthly means per place |
| **NLDAS / GLDAS** | ★★ soil moisture & ET history since 2000 (GLDAS is global) | GLDAS global 0.25°, NLDAS US | Earthdata login (GES DISC) | **Good backup for SMAP**: monthly, small, long history. Not the "GLDAS for GRACE" file downloaded before |
| **GEDI** | ★ canopy height, biomass | Global (51.6°S–51.6°N), sparse tracks | Earthdata login | Low priority: built for forests, not row crops |

### US agriculture sources (only for US places, e.g. the Iowa example)

| Source | Use | Access (tested) | Verdict |
|---|---|---|---|
| **SSURGO / STATSGO2** (NRCS) | ★★★ for US: organic matter, clay, drainage at the field | ✅ Soil Data Access REST, **no key, CORS `*`**. A SQL query with a lon/lat point returned Iowa's soil (Hanlon: 2.5 % organic matter, 15 % clay) | **Best US add-on.** Live from the browser |
| **Web Soil Survey** | Same data as SSURGO | Interactive website only | Use the SSURGO API above instead |
| **CropScape CDL** | ★★ what was planted where (30 m) → real US rotations | Open API, but needs Albers (EPSG:5070) coordinates; lon/lat returned an error | Usable with a coordinate conversion; US only |
| **NASS QuickStats** | ★★ county yields and acreage | **401 without a key** (free key by email) | Precompute in Python with the key |
| **PRISM** | ★ high-quality US climate | File downloads | Not needed: POWER covers the world |
| **OpenET** | ★ field ET, western US | **Needs a free API key** (POST) | Only if we show western-US examples |
| **CoCoRaHS** | ★ volunteer rain gauges | ✅ CSV export, no key, CORS `*` | Nice "satellite vs rain gauge" check for US/Canada |
| **USGS NWIS** | ★ groundwater, rivers | The old API now redirects (301) to the new USGS Water Data API | US only; skip for now |
| **AMS Market News** | ★ crop prices | Free key | US only; markets differ in Peru |
| **NAIP** | — 1 m aerial photos | Heavy downloads, US only | Not needed: satellite basemap already |
| **NLCD**, **LANDFIRE** | — US land cover / vegetation | Downloads | Not needed |
| **Ag Data Commons** | — catalog of USDA datasets | Catalog | Browse only if a specific dataset is needed |

### Global non-NASA and partner sources

| Source | Use | Access (tested) | Verdict |
|---|---|---|---|
| **FAO GAEZ v4** | ★★★ **crop suitability for each crop, worldwide**: exactly what our rotation scores need | Web portal (works); data downloaded per crop as rasters | **Most valuable missing piece.** Download suitability for rice, maize, sorghum, cowpea… and replace the hypothetical 1–5 scores. ⚠️ Check FAO's license terms before use |
| **Copernicus Sentinel-2** (ESA) | ★★ 10 m NDVI | ✅ STAC catalog is open (CORS); **downloads need a free Copernicus account** | HLS already includes Sentinel-2; use only if HLS fails |
| **ERA5** (ECMWF) | ★ hourly climate since 1940 | ✅ catalog open; **data needs a CDS account + key and a request queue (minutes to hours)** | Not live-friendly. POWER is enough |

## Is "everything by API" manageable?

**No, and it should not be.** Three patterns, by cost:

1. **Live in the browser** (no key, CORS ok, fast): NASA POWER, GIBS images (including IMERG and SMAP layers),
   SSURGO, CoCoRaHS. Use them for "any place on Earth".
2. **Precompute once in Python, ship small files** (login or key, slow or heavy): SMAP numbers, ECOSTRESS, HLS,
   GLDAS, IMERG numbers, NASADEM slope, NASS, GAEZ. Store per place or on the common 0.1° grid (`data/STRUCTURE.md`).
3. **Never live**: ERA5 (queue), Sentinel-2 raw, NAIP, full global SMAP. Too slow or too heavy for a demo.

Keys must never sit in the browser. If a keyed API is needed live later, add a tiny Python endpoint that holds it.

## Recommended next steps (in order)

1. **Add GIBS IMERG and SMAP layers** to the map's image-layer switch (same code as NDVI and ground heat). 10 minutes,
   instantly gives "real NASA soil moisture and rain" on the map, worldwide.
2. **Download FAO GAEZ suitability** for the example crops and use it for the "Withstand" and fit scores.
3. **Download the pending jobs**: SMAP (Harmony), ECOSTRESS and HLS (AppEEARS), and fold them into the 0.1° grid.
4. **US bonus**: when the chosen point is in the US, read SSURGO soil live and show it in the panel.
5. Rely on the browser cache for MODIS: it was unavailable (503) during this check.
