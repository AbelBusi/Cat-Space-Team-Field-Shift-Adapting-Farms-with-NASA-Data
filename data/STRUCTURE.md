# Login-only NASA data: verified structure and display plan

Checked on the real files on Nov 13, 2026. Raw files live in `data/manual/` (git-ignored, ~170 MB).
Region bbox: west −80.7, south −7.2, east −78.8, north −5.4 (Lambayeque + upper basin).

## What is here

| Folder | Dataset | Files | State |
|---|---|---|---|
| `manual/imerg/` | GPM IMERG Final monthly V07 (`GPM_3IMERGM`, `C2723754851-GES_DISC`) | 288 `.nc4`, 2001-01 → 2024-12, **complete**, 21 MB | ✅ |
| `manual/grace/` | JPL GRACE/GRACE-FO mascon CRI RL06.3 v04 (`TELLUS_GRAC-GRFO_MASCON_CRI_GRID_RL06.3_V4`, `C3195527175-POCLOUD`) | 1 `.nc`, global, 45 MB | ✅ |
| `manual/nasadem/` | NASADEM 1″ (`NASADEM_HGT` v001, `C2763264762-LPCLOUD`) | 8 `.zip` tiles, 104 MB | ✅ |
| `manual/smap/` | SMAP L3 Enhanced 9 km (`SPL3SMP_E` v006, `C2938664763-NSIDC_CPRD`) | — | ⏸ Harmony job `46f7d1a1-f4f6-40a9-aaae-8bd5f97a2429` (2023–2024, subset) |
| `manual/ecostress/` | ECOSTRESS `ECO_L3T_JET.002` (ETdaily, ETinstUncertainty, cloud, water) | — | ⏸ AppEEARS task `FieldShift_Lambayeque_ECO_JET_2024` |
| `manual/hls/` | HLS `HLSL30_VI.020` (NDVI, EVI, NDMI) | — | ⏸ AppEEARS task `FieldShift_Lambayeque_HLS_VI_2024` |

Not used, safe to delete from `~/Downloads`: `ECO_L4G_ESI_ALEXI…` (35 GB, USA only), `smapcpex_1…` (ocean wind),
`TELLUS_GLDAS-NOAH…` (a model, not GRACE), `GPM files` (empty), the 38-file IMERG folder (partial copy), 2 extra GRACE copies (same MD5).

## Real structure (and the traps)

### IMERG monthly (`manual/imerg/*.nc4`)
- HDF5 group **`Grid`**: `precipitation`, `randomError`, `precipitationQualityIndex`, `probabilityLiquidPrecipitation`,
  `gaugeRelativeWeighting`, `lat` (20), `lon` (21), `time` (1).
- `precipitation`: shape **(time=1, lon=21, lat=20)** → transpose to (lat, lon). Units **mm/hr** (monthly mean rate):
  mm/month = value × 24 × days in month. Fill −9999.9 (none found in this subset).
- Grid: lat −7.25 → −5.35, lon −80.75 → −78.75, step 0.1° → **420 cells**.
- ⚠️ `time` uses `calendar: julian` → `xarray.open_dataset(f, group="Grid", decode_times=False)` (or install `cftime`).
  Take the month from the filename: `...3IMERG.YYYYMMDD-...`.
- Reading all 288 files takes ~10 s.
- Check: Chiclayo cell = 215 mm/yr on average; **2017 = 412 mm** (the 2017 coastal El Niño), 2024 = 107 mm.

### GRACE mascon (`manual/grace/GRCTellus.JPL.200204_202609.GLO.RL06.3M.MSCNv04CRI.nc`)
- Variables: `lwe_thickness` (cm) and `uncertainty` (cm) with dims (time=261, lat=360, lon=720); `land_mask`, **`scale_factor`**,
  `mascon_ID` (lat, lon); `GAD` (cm); `*_bounds`.
- `time`: days since 2002-01-01, from Apr 2002 to Sep 2026 (with gaps, e.g. 2017–2018 between missions).
- `lon` is **0.25 → 359.75** (Lambayeque ≈ 279.3 → 281.2). Grid 0.5°, but the real mascon blocks are ~3°:
  the bbox covers only 5 × 5 grid cells and they are nearly the same signal.
- ⚠️ For land hydrology multiply `lwe_thickness × scale_factor` (JPL CRI gain factors) before computing trends.
- Check: Chiclayo cell trend without scale factor = +0.26 cm/yr.

### NASADEM (`manual/nasadem/NASADEM_HGT_<tile>.zip`)
- Each zip: `<tile>.hgt` (3601 × 3601 int16 **big-endian**, metres), `<tile>.num` (source of each pixel), `<tile>.swb` (water-body mask).
- Tile name = **south-west corner**: `s07w080` covers lat −7 → −6, lon −80 → −79. Row 0 is the north edge. Neighbouring tiles share one row/column.
- Tiles: s06w079, s06w080, s06w081, s07w079, s07w080, s07w081, s08w079, s08w080 (s08w081 is open sea).
- ⚠️ Values go down to −107 m over sea / voids: mask with `.swb` and clip to ≥ 0 on land.
- Elevation range 0 → 4 713 m (coast to Andes).

## Built: the Lambayeque grid file (in the app)

`pipeline/build_lambayeque.py` turns the three downloaded datasets into `web/public/data/lambayeque.json` (117 KB, ~10 s):
for each of the 420 IMERG cells, the typical and coastal-El-Niño monthly rain and 24 annual totals (IMERG), mean elevation,
mean slope and land share (NASADEM at ~90 m, water masked), plus the regional GRACE series and trend (scale factor applied).
The app loads it only when the chosen point is inside Lambayeque, and then uses IMERG (11 km) instead of POWER (55 km) for
rain, shows the ground (slope, erosion risk) and the underground-water trend, and can paint the rain grid on the map.

Status of the other downloads (from the download session on Nov 13–14): SMAP Harmony job still queued; AppEEARS (ECOSTRESS,
HLS and the MODIS/SMAP site requests) answered **503** for hours, so nothing from it is in the app yet. Re-run when it recovers.

## How to show it without lag

The rule: **Python does the heavy work once; the browser only loads small, ready-to-paint files, and only when a layer is opened.**

| Dataset | Pre-computed web file (in `web/public/data/`) | Size (approx.) | How it is drawn |
|---|---|---|---|
| IMERG | `lambayeque_grid.json`: for each of the 420 cells, 12-month typical rain, 12-month El Niño-years rain, 24 annual totals | ~60 KB (~15 KB gzip) | One small `<canvas>` (21 × 20 px) repainted per month → `L.imageOverlay` with `image-rendering: pixelated`. Repaint < 1 ms; no 420 SVG rectangles |
| NASADEM | `terrain_hillshade.png` + `terrain_slope.png`, mosaic resampled to ~90 m (≈ 2 300 × 2 200 px); plus slope and elevation per IMERG cell inside `lambayeque_grid.json` | ~1–2 MB total | Two `L.imageOverlay` (hillshade under, slope classes on top with opacity). Point values come from the grid file, not from the image |
| GRACE | Series for the bbox cells (with `scale_factor`) + 1 trend value per cell, inside `lambayeque_grid.json`; optional global trend PNG 720 × 360 for the world view | ~30 KB + ~100 KB | Sparkline and a "region is gaining / losing water" badge; PNG overlay at world zoom |
| SMAP / ECOSTRESS / HLS (when downloaded) | Monthly means aggregated **to the same 0.1° IMERG grid** (added as more fields per cell), plus 12 monthly NDVI PNGs for the field view | ~10–50 KB each; PNGs ~100 KB | Same canvas overlay as IMERG; NDVI PNGs as image overlays at field zoom |

Why this is fast:
- **One common grid (IMERG 0.1°, 420 cells)** holds every variable, so the map, the panel and a future k-means "zones" model all read the same small file.
- **Canvas / image overlays instead of thousands of SVG shapes.** Leaflet's DOM shapes get slow after a few hundred; one image is one DOM node.
- **No Vue reactivity on big arrays**: keep them in `shallowRef` or `markRaw`, and only the selected values in reactive state.
- **Lazy loading**: the grid file loads when the map section appears; terrain PNGs only when the "Terrain" layer is switched on.
- **Quantised numbers** (rain in whole mm, slope in 0.1°) and gzip from the static host keep files tiny.
- Live APIs (NASA POWER, GIBS) stay for "any point on Earth"; the pre-computed files make **Lambayeque instant and offline-safe** for the demo.

## For coastal Peru: which El Niño index (applied in the app)

NOAA's ONI (central Pacific) did **not** flag 2017, yet IMERG shows it as the wettest year on the Lambayeque coast (coastal El Niño).
For this region also use **Niño 1+2** (NOAA, `https://www.cpc.ncep.noaa.gov/data/indices/sstoi.indices`) or Peru's **ICEN** index (ENFEN).

**Checked in the data:** with ONI years, the Chiclayo cell shows *less* rain than usual (187 vs 217 mm a year). Using
Jan–Apr Niño 1+2 anomaly ≥ 0.8 °C gives 1983, 1998, 2016, 2017 and 2023, exactly Lambayeque's flood years. The app uses this
list (`NINO_COASTAL` in `web/src/lib/nasa.js`) inside Lambayeque, and ONI elsewhere.
