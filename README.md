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

**One screen, like a game.** Sprout says hello and asks if you want a guide. Then you pick your province and district on a
map of Lambayeque (or "Use my location", or "Free mode" for the whole department). The satellite map opens **cut to that
territory**, with town and village names, and the topics come one at a time with the side arrows: satellite signals → ground and
recent weather → year by year → what matters to you → rotations → comparison → report. The **PDF** button prints the full report.
Sprout can be turned off (it waits as a small tab and raises a `!` when it has something to say) and answers open questions.

**Asking Sprout anything:** set `VITE_ASK_URL` (in `web/.env.local`) to a small server that holds the AI key and answers
`POST { question, lang, context }` with `{ answer }`. Never put an AI key in the browser. Without it, Sprout answers a few
topics locally (NDVI, soil moisture, El Niño, satellite squares, rotations, salty soil) and says the AI is not connected.

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
| `web/src/content.js` | **All page text**: signals, crops, rotations, glossary, the topics (`SLIDES`) and Sprout's lines (`SCRIPTS`) |
| `web/src/guide.js` | Sprout's dialogue: lines, answers to pick, guide on/off, open questions |
| `web/src/cat/` | `sprites.js` (pixel art as text rows), `CatSprite.vue`, `SproutDock.vue` |
| `web/src/components/` · `web/src/slides/` | The stages, the clipped satellite map and the HUD pieces · one file per topic |
| `web/src/data/` · `pipeline/build_districts.py` · `pipeline/build_places.py` | Lambayeque boundaries and place names from OpenStreetMap |
| `pipeline/` | Python for datasets that need a login (GPM, SMAP, HLS, GRACE-FO) and `fetch_power.py` for quick checks |
| `data/` | Downloaded open data for 10 places, and **the list of login-only datasets with step-by-step routes** (`data/README.md`) |
| `pipeline/fetch_open_data.py` | Re-downloads all open data (POWER, MODIS NDVI, SoilGrids, NOAA ONI) for `data/places.csv` |
| `docs/LANGUAGES.md` | English / Spanish / Quechua switch: how translations work and the Quechua review status |
| `docs/STACK.md` | Every technology with its version, the architecture, where each on-screen number comes from, scripts and troubleshooting |
| `docs/PROBLEM_AND_IMPACT.md` | **For the pitch:** the problem, who is affected, user segments, our solution, expected benefits and statistics, with scientific references |
| `docs/LAMBAYEQUE_RISKS.md` | Phase 1 focus: coastal El Niño (in the app) and soil salinity (plan) |
| `pipeline/build_lambayeque.py` | Builds `web/public/data/lambayeque.json`, the Lambayeque 0.1° grid (IMERG rain, NASADEM terrain, GRACE water) |
| `COMMITS.md` | Commit convention (Conventional Commits) and the pull-before-push workflow |
| `docs/RESOURCES_GUIDE.md` | The 25 official challenge resources: what we have, what works by API, what needs a login or a download |
| `docs/DATA_SOURCES.md` | Every data source, ranked by usefulness, with how to get it and how to cite it |

## Sprout, the guide

![Sprout's 10 moods, sitting and waving: neutral, happy, excited, surprised, worried, thinking, sad, shy, determined, sleepy](docs/sprout-moods.png)

- Gentle, patient and encouraging. It explains one thing at a time and is honest about what the satellites cannot see.
- A full-body sitting alien cat (48 × 50 px, original pixel art) with 10 moods: `neutral`, `happy`, `excited`, `surprised`, `worried`,
  `thinking`, `sad`, `shy`, `determined`, `sleepy`, two poses (`sit`, `wave`) and four antenna shapes. It blinks, wags its tail, bobs,
  and moves its mouth while text types. The dialogue shows only its head.
- **Arrival:** on each visit its saucer glides in, opens a beam and sets Sprout down by the campfire; it lands, waves, the saucer
  leaves and only then it talks (skipped with reduced motion).
- Its voice is a synthesized meow (`web/src/lib/sound.js`, no audio files): one meow per mood change, tiny mews while text types, and a meow when you tap it at the top of the page. Tune the `MEOW` table by ear.
- **Add or edit a line:** `SCRIPTS` in `web/src/content.js`, one entry per screen. Each line is `[text, mood]`; add its Spanish
  and Quechua in `web/src/i18n.js`. Keep it short: the screen already shows the data, Sprout only explains it.
- **Redraw the cat:** edit `pipeline/draw_sprout.py` (shapes for the body, small stamps for each face) and run
  `python pipeline/draw_sprout.py web/src/cat/sprites.js docs/sprout-moods.png`.
- Visitors can turn the guide off (top bar or Sprout's answers), mute the voice blips, or minimize the box. With *reduced
  motion* enabled in the operating system, text and charts appear without animation.

## Animations (and where)

| Where | What moves |
|---|---|
| Intro | Outer Wilds night scene: twinkling stars, a satellite on its orbit sending signal rings, silhouettes of the Andes and algarrobo trees, a flickering campfire with Sprout |
| Region picker | The hills sink and the sky opens; provinces and districts pop in one after another; the camera glides into the province you tap and dives into the district |
| Map | The satellite photo appears cut to the territory, the outline draws in; town names fade in as you zoom; the climate square takes the color of the signal and month |
| Topics | Cards slide in from their side one after another; numbers count, sparklines and warming stripes draw on; rotation rows re-sort and their 12 plants rise in order |
| Detail | Topic-by-topic squares with better/worse arrows; the confidence meter fills cell by cell |

## Team checklist before the event (Nov 14)

- [ ] Each member: create a free Earthdata Login account and approve "NASA GESDISC DATA ARCHIVE" (see `docs/DATA_SOURCES.md`).
- [ ] Nov 13: read the challenge's Resources tab and update the ranking in `docs/DATA_SOURCES.md`.
- [ ] Ask the Local Lead what prepared code is allowed at the start.
- [ ] Decide which tier B dataset to add first (suggestion: GPM IMERG for rain extremes, then GRACE-FO for groundwater).

## License

Apache-2.0, the Space Apps default for original content unless you choose another OSI license. Third-party data and
libraries are listed with their licenses in `docs/DATA_SOURCES.md`.
