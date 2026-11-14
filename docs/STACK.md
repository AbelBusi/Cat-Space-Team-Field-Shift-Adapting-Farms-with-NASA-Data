# Tech stack and architecture

Everything the project uses, why, and how the pieces connect. Versions are the ones installed on Nov 14, 2026
(`web/package-lock.json`, `pipeline/requirements.txt`). Install everything with `./setup.sh`.

## 1. Architecture in one picture

```
                    ┌──────────────────────────── browser (the whole app runs here) ─────────────────────────────┐
                    │                                                                                            │
 NASA POWER API ────┼──► lib/nasa.js fetchPower()  ─┐                                                            │
 ORNL MODIS API ────┼──► lib/nasa.js fetchNdvi()   ─┤                                                            │
 NASA GIBS tiles ───┼──► Leaflet map layers         │   store.js (state, ranking, risks, history)                │
 Nominatim (OSM) ───┼──► lib/nasa.js searchPlaces() ├──► ───────────────────────────────► Vue components ──► page │
                    │                               │   guide.js (Sprout's script)                               │
 public/data/       │                               │                                                            │
  lambayeque.json ──┼──► store.js local / cell ─────┤   ◄── built offline by pipeline/build_lambayeque.py        │
                    └────────────────────────────────────────────────────────────────────────────────────────────┘

 Offline (Python, run by a person with an Earthdata login):
   data/manual/{imerg,grace,nasadem}  ──► pipeline/build_lambayeque.py ──► web/public/data/lambayeque.json
   NASA POWER / ORNL / SoilGrids / NOAA ──► pipeline/fetch_open_data.py ──► data/{power,ndvi,soil}/, data/oni.txt
```

- **No backend.** Every live API used accepts browser calls without a key (CORS `*`). The site is static and can be hosted
  anywhere (GitHub Pages, Netlify, Vercel) with `npm run build`.
- **APIs first, files as backup** (AGENTS.md rule 7): live APIs for anywhere on Earth; pre-built files when NASA has no keyless
  API (IMERG numbers, GRACE, NASADEM) and for Lambayeque, which loads from the grid file.

## 2. Web app (`web/`)

| Package | Version | Used for | License |
|---|---|---|---|
| Vue | 3.5.45 | UI components, reactivity | MIT |
| Vite | 8.3.8 | Dev server and build | MIT |
| @vitejs/plugin-vue | 6.0.10 | `.vue` files in Vite | MIT |
| Leaflet | 1.9.4 | The map, tile layers, field outline | BSD-2-Clause |
| D3 | 7.9.2 | Color ramps, scales, sparkline and chart shapes | ISC |
| @fontsource/atkinson-hyperlegible | 5.3.0 | Body text | OFL-1.1 font |
| @fontsource-variable/bricolage-grotesque | 5.3.0 | Headings | OFL-1.1 font |
| @fontsource/ibm-plex-mono | 5.3.0 | HUD labels, numbers, Sprout's text | OFL-1.1 font |
| @fontsource/pixelify-sans | 5.3.0 | Sprout's name tag | OFL-1.1 font |

Node 20+ (tested on 24.21). No CSS framework: plain CSS with the variables of `DESIGN.md` in `web/src/style.css`.

### Source map

| File | Role |
|---|---|
| `src/main.js` · `src/App.vue` | Entry, top bar (language, Farmer/Pro, theme), section order, page atmosphere |
| `src/content.js` | **All text**: layers and their plain-language readings, Farmer words (`levelWord`), crops, rotations, glossary, Sprout's `SCRIPTS` |
| `src/store.js` | State, live data loading (`selectPoint`), the Lambayeque grid (`local`, `cell`), rotation `ranking`, `risks`, `history` |
| `src/guide.js` | Sprout's dialogue queue, which section is talking, what each `<Reveal>` shows |
| `src/lib/nasa.js` | NASA POWER, ORNL MODIS, POWER daily, GIBS layer list, place search, grid-cell geometry, El Niño year lists |
| `src/lib/geo.js` | Field outline math (area, perimeter, center) and coordinate parsing |
| `src/lib/palette.js` | `PAL` and `RAMP` (DESIGN.md colors) for Leaflet, D3 and canvas |
| `src/lib/pixelIcons.js` · `src/lib/landmask.js` | 16 × 16 pixel icons · 120 × 60 Earth land mask (from GRACE) for the pixel globe |
| `src/lib/sound.js` · `src/lib/tween.js` | Synthesized meows and melody · number/array tweening |
| `src/cat/` | Sprout's sprites (`sprites.js`), `CatSprite.vue`, the translator panel `CatDialogue.vue` |
| `src/components/` | One component per section (`HeroSection`, `MapSection`, `SignalPanel`, `YearsSection`, `Priorities`, `Rotations`, `RotationDetail`, `Glossary`) plus building blocks (`Reveal`, `PixelIcon`, `Instrument`, `PixelGlobe`, `FieldRow`, `TradeOffs`, `Sparkline`, `OrbitSky`) |
| `public/data/lambayeque.json` | The Lambayeque 0.1° grid (IMERG, NASADEM, GRACE) |

### Performance rules (why it does not lag)

- Big data arrays are never deeply reactive (`shallowRef` for the grid file).
- The 420 rain cells are painted on one 21 × 20 canvas and shown as **one image** (`L.imageOverlay`), not 420 shapes.
- Files load only when needed (the grid only when the point is inside Lambayeque).
- Animations use CSS and `requestAnimationFrame`; all of them stop with `prefers-reduced-motion`.

## 3. Data pipeline (`pipeline/`)

Python 3.11+ (tested on 3.14) in `pipeline/.venv`.

| Package | Version | Used for | License |
|---|---|---|---|
| earthaccess | 0.19.0 | Earthdata login, NASA search and download | MIT |
| xarray | 2026.9.0 | Gridded data (NetCDF/HDF5) | Apache-2.0 |
| h5netcdf · h5py | 1.8.3 · 3.16.0 | Reading IMERG, GRACE, SMAP files | BSD-3-Clause |
| numpy · pandas | 2.5.4 · 3.1.1 | Arrays and tables | BSD-3-Clause |
| scikit-learn | 1.9.1 | Optional k-means zoning of grid cells | BSD-3-Clause |

| Script | What it does | Needs |
|---|---|---|
| `fetch_power.py <lat> <lon>` | Prints NASA POWER climatology for a point | Internet |
| `fetch_open_data.py` | Downloads POWER, MODIS NDVI, SoilGrids and NOAA ONI for `data/places.csv` | Internet |
| `fetch_earthdata.py` | Downloads GRACE, NASADEM and IMERG with `earthaccess` | Earthdata login (`~/.netrc`) |
| `build_lambayeque.py` | Builds `web/public/data/lambayeque.json` from `data/manual/` | The downloaded files |

## 4. Where each number in the app comes from

| On screen | Inside Lambayeque | Anywhere else | If the service is down |
|---|---|---|---|
| Daytime heat, frost, soil wetness | NASA POWER (live, ~55 km) | Same | — |
| Rain (monthly) | **GPM IMERG 0.1°** (downloaded, 2001–2024) | NASA POWER (live) | Grid file (Lambayeque) |
| El Niño scenario | **Coastal**: Niño 1+2 years 1983, 1998, 2016, 2017, 2023 | ONI years | — |
| Plant greenness | MODIS via ORNL (live, 250 m, cached) | Same | Browser cache (ORNL often answers 503/504) |
| Underground water | **GRACE-FO** regional trend (downloaded) | "Coming soon" | — |
| Ground (elevation, slope, erosion) | **NASADEM** cell mean (downloaded) | Not shown | — |
| Last 30 days | NASA POWER daily (live) | Same | — |
| Year by year (1981–2024) | NASA POWER monthly (live) | Same | — |
| Map images | GIBS: NDVI, ground heat, **IMERG rain, SMAP soil moisture** (live); **rain grid 0.1°** (downloaded) | GIBS layers | — |
| Rotation scores, confidence | **Hypothetical expert rules** (labelled) | Same | — |

**Big outlined fields.** A field can be bigger than one data square (e.g. the Olmos project). Inside Lambayeque, rain
(IMERG) and ground (NASADEM) become the **area-weighted average** of every 0.1° square the field touches: a 40 × 40 net of points
over the outline counts how much of the field falls in each square (`cover` and `cell` in `store.js`). The squares are drawn
dashed on the map, and Sprout says how many there are and the range of yearly rain between them. NASA POWER (55 km) and MODIS
(250 m) are still read at the field's center; Sprout warns when the field crosses several POWER squares or is over 25 ha.

## 5. Commands

```bash
./setup.sh                                   # install web + Python
cd web && npm run dev                        # http://localhost:5173
cd web && npm run build                      # static site in web/dist
pipeline/.venv/bin/python pipeline/build_lambayeque.py   # rebuild the Lambayeque grid
```

## 6. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `sh: vite: Permission denied` | `node_modules` came from git without exec permissions | `rm -rf web/node_modules && cd web && npm ci` |
| Plant greenness stuck on "Listening…" | ORNL MODIS service slow or down (503/504) | Wait and tap the place again (results are cached in the browser) |
| Earthdata download 401/403 | The data center's app is not authorized | urs.earthdata.nasa.gov → Applications → Authorized Apps: approve GES DISC, LP DAAC, PO.DAAC, NSIDC |
| AppEEARS files return 503 | AppEEARS storage outage | Retry later; nothing in the app depends on it yet |
| `xarray` "unable to decode time units … julian" | IMERG files use a julian calendar | `open_dataset(..., decode_times=False)` |
