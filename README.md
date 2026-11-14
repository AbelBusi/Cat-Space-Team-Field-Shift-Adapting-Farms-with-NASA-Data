# Field Shift · Cat Space Team

NASA Space Apps Challenge 2026, **Field Shift: Adapting Farms with NASA Data**. Cat Space Team, Chiclayo, Peru.

This is a decision-support tool that turns NASA Earth observations into plain language, so a farmer **anywhere on Earth** can
compare crop rotations. Pick a spot on the map. The app fetches real NASA data for the grid cell that covers it, and a friendly
alien cat, **Sprout**, explains each part while it appears.

> The page is in **English** (Space Apps rule). Live data: NASA POWER (heat, rain, soil wetness, frost) and MODIS NDVI.
> Still hypothetical: the rotation scores (1–5 per topic) and the confidence meter.

> **Design rules:** [`DESIGN.md`](DESIGN.md) (agreed palette, square corners, fonts, pixel icons, chart rules).
> **For AI agents:** [`AGENTS.md`](AGENTS.md) (also loaded as `CLAUDE.md` / `GEMINI.md`).

## Quick start

Requirements: Node 20+ and Python 3.11+ (Linux or macOS; on Windows use Git Bash or WSL).

**New teammate? One line gets the whole stack:**

```bash
git clone https://github.com/AbelBusi/Cat-Space-Team-Field-Shift-Adapting-Farms-with-NASA-Data.git && cd Cat-Space-Team-Field-Shift-Adapting-Farms-with-NASA-Data && ./setup.sh && cd web && npm run dev
```

**1. Install everything with one command** (from the `field-shift` folder):

```bash
./setup.sh          # Vue + Python
./setup.sh web      # only the Vue app (web/node_modules)
./setup.sh python   # only the Python libraries (pipeline/.venv)
```

Run it again whenever `package.json` or `pipeline/requirements.txt` changes, or after copying the project to a new folder
(`node_modules` and `.venv` are not meant to be copied).

**2. Run the app:**

```bash
cd web
npm run dev          # http://localhost:5173
npm run build        # static site in web/dist (fonts included; the NASA data needs internet)
```

**Example places.** The map offers six places in Lambayeque (Chiclayo, Lambayeque, Ferreñafe, Mórrope, Motupe, Olmos),
set in `PLACES` in `web/src/content.js`. Search still works anywhere, but phase 1 polishes Lambayeque only.

**3. Python (datasets that need an Earthdata login, hackathon work):**

```bash
pipeline/.venv/bin/python pipeline/fetch_power.py -6.77 -79.84   # quick check: NASA POWER climate normals, no login
```

| What `setup.sh` installs | Where | Libraries |
|---|---|---|
| Web app | `web/node_modules` | Vue, Vite, D3, Leaflet, fonts (see `web/package.json`) |
| Data pipeline | `pipeline/.venv` | earthaccess, xarray, h5netcdf, pandas, numpy, scikit-learn (see `pipeline/requirements.txt`) |

## How it works

```
click on the map ──► grid cells around the point (lib/nasa.js → gridCells)
                 ──► NASA POWER monthly 2001–2024 ──► typical year + El Niño years   (≈1 s)
                 ──► MODIS NDVI 2024 via ORNL DAAC ──► monthly greenness             (≈40–60 s, cached in the browser)
                 ──► panel, rings, risks and Sprout's words update
```

- **Map tools** (ported from the team's React + MapLibre prototype, commit `17a23cb`): place search by name or coordinates,
  "My location", **outline my field** (corners → area, perimeter and a center point used for all the data), NASA GIBS image
  layers (vegetation health, ground heat) with an intensity slider, the last 30 days of rain and temperature, and a detailed
  satellite base map (Sentinel-2 cloudless + Esri; check their licenses in `docs/DATA_SOURCES.md`).
- **No backend.** NASA POWER, the ORNL DAAC MODIS service and NASA GIBS map tiles all accept calls straight from the browser,
  without a login. So the app works for any point on Earth.
- **Grid cells ("cuadrantes").** Each dataset sees the ground in squares of a different size. The map draws them nested around
  the chosen point: POWER ≈ 55 km, GPM IMERG 0.1°, SMAP ≈ 9 km, MODIS ≈ 250 m and HLS ≈ 30 m. POWER and IMERG follow their real
  lat/lon grids; SMAP, MODIS and HLS use other projections, so their squares are approximate.
- **Typical year vs El Niño years.** "Typical" averages every month of 2001–2024. "El Niño" averages only the years of El Niño events
  by NOAA's ONI (2003, 2005, 2007, 2010, 2015, 2016, 2019, 2024).
- **Daytime heat** is the typical afternoon high, estimated as `T2M + T2M_RANGE / 2`. POWER's monthly `T2M_MAX` is the single hottest
  hour of the month, so it is not used for that. **Frost risk** = the coldest hour of the month is below 0 °C on average.
- **Rotations** are four example rotations from the Peruvian coast. Warnings adapt to the climate of the cell (dry, cool, El Niño rain).
  Growing the crop library for other regions is hackathon work.

| Path | What it holds |
|---|---|
| `web/src/lib/nasa.js` | Live NASA requests (POWER, MODIS, GIBS layers), place search and the grid-cell geometry |
| `web/src/lib/geo.js` | Field outline math: area, perimeter, center; coordinate parsing |
| `web/src/store.js` | Chosen point, loaded data, rotation ranking and risk months |
| `web/src/content.js` | **All page text**: signals, example places, crops, rotations, glossary and Sprout's lines (`SCRIPTS`) |
| `web/src/guide.js` | Dialogue logic: which section is talking, what is revealed |
| `web/src/cat/` | `sprites.js` (pixel art as text rows), `CatSprite.vue`, `CatDialogue.vue` |
| `web/src/components/` | One component per section, plus `Reveal`, `YearRing`, `Radar`, `Sparkline`, `OrbitSky` |
| `pipeline/` | Python for datasets that need a login (GPM, SMAP, HLS, GRACE-FO) and `fetch_power.py` for quick checks |
| `data/` | Downloaded open data for 10 places, and **the list of login-only datasets with step-by-step routes** (`data/README.md`) |
| `pipeline/fetch_open_data.py` | Re-downloads all open data (POWER, MODIS NDVI, SoilGrids, NOAA ONI) for `data/places.csv` |
| `docs/LANGUAGES.md` | English / Spanish / Quechua switch: how translations work and the Quechua review status |
| `docs/STACK.md` | Every technology with its version, the architecture, where each on-screen number comes from, scripts and troubleshooting |
| `docs/LAMBAYEQUE_RISKS.md` | Phase 1 focus: coastal El Niño (in the app) and soil salinity (plan) |
| `pipeline/build_lambayeque.py` | Builds `web/public/data/lambayeque.json`, the Lambayeque 0.1° grid (IMERG rain, NASADEM terrain, GRACE water) |
| `COMMITS.md` | Commit convention (Conventional Commits) and the pull-before-push workflow |
| `docs/RESOURCES_GUIDE.md` | The 25 official challenge resources: what we have, what works by API, what needs a login or a download |
| `docs/DATA_SOURCES.md` | Every data source, ranked by usefulness, with how to get it and how to cite it |

## Sprout, the guide

![Sprout's 7 moods: neutral, happy, surprised, worried, thinking, sad, shy](docs/sprout-moods.png)

- Gentle, patient and encouraging. It explains one thing at a time and is honest about what the satellites cannot see.
- 7 moods: `neutral`, `happy`, `surprised`, `worried`, `thinking`, `sad`, `shy`. It blinks, bobs, and moves its mouth while text types.
- Its voice is a synthesized meow (`web/src/lib/sound.js`, no audio files): one meow per mood change, tiny mews while text types, and a meow when you tap it at the top of the page. Tune the `MEOW` table by ear.
- **Add or edit a line:** `SCRIPTS` in `web/src/content.js`. Each line is `[text, mood]`. Line *i* of a section reveals every
  `<Reveal :at="i">` block inside that section.
- **Redraw the cat:** edit the character rows in `web/src/cat/sprites.js` (one character = one pixel, `.` = transparent, colors in `PALETTE`).
- Visitors can skip everything ("Show everything"), mute the voice blips, or hide the box. With *reduced motion* enabled
  in the operating system, text and charts appear without animation.

## Animations (and where)

| Where | What moves |
|---|---|
| Landing | Outer Wilds night scene: twinkling stars, a satellite on its orbit sending signal rings, silhouettes of the Andes and algarrobo trees, a flickering campfire with Sprout |
| Map | The map flies to the chosen spot, and the grid cells appear nested from the biggest to the smallest. The NASA POWER cell takes the color of the signal and month, and pulses while data loads |
| Panel | Sparklines draw on, numbers count to new values, the resolution square resizes |
| Rotations | Cards re-sort with a smooth slide when priorities change; each year is a row of 12 pixel plants (seed, growing, stressed, harvest, bare soil) that rise in order; risk icons on top; scores count |
| Detail | Topic-by-topic squares with better/worse arrows; the confidence meter fills cell by cell |

## Team checklist before the event (Nov 14)

- [ ] Each member: create a free Earthdata Login account and approve "NASA GESDISC DATA ARCHIVE" (see `docs/DATA_SOURCES.md`).
- [ ] Nov 13: read the challenge's Resources tab and update the ranking in `docs/DATA_SOURCES.md`.
- [ ] Ask the Local Lead what prepared code is allowed at the start.
- [ ] Decide which tier B dataset to add first (suggestion: GPM IMERG for rain extremes, then GRACE-FO for groundwater).

## License

Apache-2.0, the Space Apps default for original content unless you choose another OSI license. Third-party data and
libraries are listed with their licenses in `docs/DATA_SOURCES.md`.
