# Field Shift design system

**Agreed by the whole team on Nov 13, 2026. Do not add colors, shapes or fonts outside this file.**
If something seems to need a new color, it does not: use a ramp step, a pattern, an icon or a text label instead.
The tokens below live as CSS variables at the top of `web/src/style.css`, as **Tailwind colors** (`bg-panel`, `text-ink`,
`border-line`, `text-teal`, `bg-fire`… Tailwind's own palette is switched off), and as `PAL` / `RAMP` in `web/src/lib/palette.js`
for Leaflet, D3 and canvas code. Always use those, never a raw hex.

Mood: **Outer Wilds at night**. A calm, cozy space-camp feeling: deep night sky, a turquoise glow, a warm campfire.
Data must still read clearly, so data colors are *derived* from the same two accents.

## 1. Palette

### Interface (5 neutrals + 2 accents)

| Token | Hex | Use | Never |
|---|---|---|---|
| `--bg` | `#0B1026` | Page background, the "space" | — |
| `--panel` | `#121A3A` | Panels, cards, the map frame, Sprout's screen | — |
| `--line` | `#1E2A52` | 1 px borders, chart grid lines, dividers | Text |
| `--muted` | `#8C9BC4` | Secondary text, axis labels, captions | Long paragraphs |
| `--ink` | `#F2E8D5` | Main text, icons by default | — |
| `--teal` | `#4FC1B6` | **The accent.** Links, active state, selected items, focus ring, "normal" data | Warnings |
| `--fire` | `#F2A541` | **The campfire.** At most ONE highlighted thing per screen: the main button, the key number, the highlighted bar | Decoration, backgrounds |

There is **one look only: the night camp.** The light mode was removed on Nov 15, 2026 (not needed, and the team preferred the night).

### Data (derived, only inside charts, maps and legends)

| Token | Hex | Use |
|---|---|---|
| `--sand` | `#D8C08E` | Dry, bare soil, low risk |
| `--soil` | `#A88B5A` | Soil in icons, the ground line of charts |
| `--sage` | `#9CC5A1` | Middle of the vegetation ramp |
| `--deep` | `#2E6E86` | Dark end of the water ramp, plant outlines |
| `--ember` | `#E0703A` | High risk, extreme heat. The only "alarm" color |
| `--ghost` | `#A99BE8` | Frost, and the 4th category when 4 are needed |

**Ramps** (always these stops, in this order):

| Meaning | Stops |
|---|---|
| Amount (rain, soil moisture) | `--line` → `--deep` → `--teal` → `#BFEDE6` |
| Vegetation (NDVI) | `--sand` → `--sage` → `--teal` → `--deep` |
| Temperature (absolute) | `--deep` → `--sand` → `--fire` → `--ember` |
| Anomaly (diverging) | `--teal` (cooler / wetter) → `#2A3A66` (normal) → `--fire` → `--ember` (hotter / drier) |
| Risk (3 levels, not a traffic light) | `--sand` low · `--fire` medium · `--ember` high |
| Categories (max 4, this order) | `--teal`, `--fire`, `--sand`, `--ghost` |

No red, yellow or green "traffic lights". No rainbow ramps (jet, viridis, turbo). No colors from chart-library defaults.

## 2. Shape

- **Square corners everywhere** (`border-radius: 0`). No pills, no bubbly cards, no rounded buttons, also in Leaflet controls.
- Borders are **1 px `--line`**. A featured panel may add **HUD corner brackets** (the `.hud` class), like a ship screen.
- No shadows, no blur, no glassmorphism, no gradients **on components**. Gradients live only in the **atmosphere**: the landing sky
  and the fixed page background (soft teal, campfire and lavender lights, faint stars; the campfire glow grows as you scroll).
  Cards may be slightly see-through (88 % panel) so that light shows behind them, but never blurred.
- Buttons are text in **mono caps inside brackets or a 1 px frame**: `[ NEXT ]`, `EXPLORE`. The single main action uses `--fire`.

## 3. Type

| Role | Font | Size |
|---|---|---|
| Headings | Bricolage Grotesque, weight 600 | h1 max **40 px** desktop / 30 px mobile; h2 24–28 px. No giant hero letters |
| Body | Atkinson Hyperlegible | 16 px, line-height 1.5 |
| HUD labels, numbers, buttons, Sprout's text | IBM Plex Mono | 12–15 px; labels in caps with 0.08em spacing |
| Sprout's name tag only | Pixelify Sans | 13 px |

## 4. Icons

Use only the pixel icons in `web/src/lib/pixelIcons.js` through `<PixelIcon name="…" />` (16 × 16, scaled by whole numbers).
They speak the farmer's language: a plant that is fine, thirsty or dead says more than a red dot.

| Icon | Means |
|---|---|
| `plant_ok` | Healthy crop, good conditions |
| `plant_thirsty` | Water stress, risk of loss |
| `plant_dead` | Crop loss, high risk |
| `seed` · `harvest` · `bare` | Sowing month · harvest month · bare soil |
| `sun` · `drop` · `rain` · `frost` | Heat · irrigation water · heavy rain · frost |
| `rice` · `maize` · `cowpea` · `sorghum` · `green_manure` | The crops of the example rotations (Lambayeque). Shown in order with their months (`CropSequence`) wherever a rotation is named |
| `satellite` · `calendar` · `heart` · `compare` · `report` | The topics of the map screen: what the satellites see · year by year · what matters to you · compare with today · your report |
| `up` · `down` · `flat` | Trend. Color = what it means for the crop: `--ember` worse, `--teal` better, `--ink` neutral |

Line icons (stroke SVG) are allowed only for UI controls (play, sound, close), drawn in `--ink` or `--muted`.

## 5. Charts

- **One story per chart.** The bar, point or month that matters is `--fire` with its label; everything else is `--teal` at 35 % opacity.
- Grid lines `--line`, axis labels `--muted` in mono. No pie, donut, 3D or gauge charts. No legends when a direct label fits.
- Prefer farm metaphors: a year is a **row of 12 plants** (sown, growing, harvested, bare); risk is a plant's state; trend is an arrow.
- Every number on screen is rounded and has its unit.

## 6. Map

- The base map is always **real satellite imagery, untouched**. Farmers must see their field as it is.
- The satellite map is **cut to the chosen territory** (a district, or the whole department in free mode): outside its outline
  the night sky shows, never the neighbouring regions or the ocean. The outline is a 4 px `--teal` line. The cut follows every
  pan and zoom (also during the zoom animation), so nothing outside ever flashes.
- Town and village names (OpenStreetMap) sit on the photo like on a road map: `--sky-ink` text with a thin dark outline. This text
  outline is the one allowed "shadow", because a label must read on any ground. Bigger places first, no overlapping names.
- NASA data are **optional overlays** on top, with the ramps above, a legend and an opacity control.
- **3D view of an outlined field:** it opens by itself when a field is finished; the 2D / 3D switch next to the field size and
  the time bar under the block (below) are its only controls (no other panel, titles or buttons). The cards stay on screen. On the map the field stays lit and everything
  around it goes almost dark; the field moves to the lower part of the free space and **the field rises out of it as a floating
  block of land**, joined to it by a faint `--teal` beam, like a projection, but the block is full quality: the satellite photo
  over the real relief, soil layers on the sides, the `--fire` outline on top. It floats gently and turns slowly (drag to turn,
  wheel or pinch to zoom). Measurements are drawn, not written: a `--teal` height line on the uphill side and the slope angle
  (level line dashed, land line solid, an arc between) on the downhill side, each with a short label. Small relief is raised and
  the factor is always shown (`Relief ×N`); the height source is in the map credits. The area sits over the block in a `--fire`
  frame, and each side shows its real length on its edge (only when the side is long enough on screen). Everything on the map except the field
  sits under a dark veil (86 %), so only the field and its block stand out; the cards stay readable. A compass rose turns with
  the view; tapping it swings the block back to north up.
- **Field log (time bar), only in "What's ahead":** a HUD strip under the block, drawn like a ship log: a `--line` grid,
  the deep soil water (28–100 cm) of the 2 km square at the field's centre every month since 1998 in `--teal`, El Niño years
  as `--line` blocks, and log entries above the line (square cards: a `--teal` header with the year, a pixel icon below)
  for each run of El Niño years and the driest year, joined in time order by `--ink` arrows. The coming year takes the
  right third: its band, its dashed middle and the entry **"?"** with a dashed border, like an entry still unknown. It
  opens pointing at the coming year. After it, 2027–2030 (one point per year) carry the 1998–2025 trend of the deep soil
  drawn on, dashed `--ink` with its band, and an entry "2030 · trend" with an up / down / flat icon; the trend line also
  crosses the past. That part always says "if the 1998–2025 trend continues" and that it is a direction, not a number
  (`docs/ML_TRENDS.md`). The chosen month is the one `--fire` mark (cursor and the current entry). Drag on
  the screen or use the arrow keys; the play button runs 1998 → the end. The month of the projection is the same as the
  map's month. Under the screen: the month and one plain sentence (much / a little wetter, usual, a little / much drier
  than usual for this month), and the three layers. The block's sides are the three ERA5-Land layers (0–7, 7–28,
  28–100 cm, the thin top ones drawn a little thicker): each fills with `--deep` water as that layer gets wetter for this
  place that month, hatched where there is no value (the projection only knows the deep layer). In "Today" the topic's own
  month card already chooses the month, so there is no log there. On phones it is compact (years every 10, no layer words).

## 7. One screen, like a game (layout since Nov 15, 2026)

No page scrolling. Three stages on the same night sky:

1. **Intro:** Sprout, big, says who it is and offers answers (guide me · I'll explore alone · ask something else).
2. **Where do you farm?** Lambayeque drawn flat in the data categories (`--teal`, `--sand`, `--ghost` per province). Tap a
   province, the camera glides into it and shows its districts with their names; tap a district to fly in. "Use my location"
   and "Free mode" are always there.
3. **Explore:** the clipped satellite map fills the screen. One **topic** at a time floats over it: cards on the left and right
   edges (at most two per side, one idea per card), the topic title at the top over a path of pixel icons (one per topic: done
   in `--teal`, current in `--fire`, ahead dimmed) and a "Next: …" line, and large `‹ ›` arrows on the sides
   (keyboard arrows too). On phones the cards become one bottom sheet and the map stays on top.

Prefer a pixel icon next to a short label over a paragraph: the signals, the satellites, the crops, gains (`up`) and risks
(`down`) all carry one.

Attention rule: never show everything at once. A topic shows only what its title promises; details go in a `<details>` or the
printed report.

## 8. Sprout's panel (Outer Wilds translator style)

- A panel at the bottom of the screen: `--panel` background, `--teal` frame with HUD brackets, label `SPROUT · TRANSLATOR` in mono caps.
- Text in IBM Plex Mono, `--ink`, typed letter by letter. Answers to pick appear as buttons under the text (keys 1–9 work).
- Personality: gentle, a little shy, always encouraging, never pushy (Ralsei-like). It explains a screen once, only with the
  guide on. With the guide off it waits as a small tab and raises a `--fire` `!` when it has something worth saying.
- Data never wait for Sprout: every topic shows its content at once; Sprout only talks about it.

## 9. Motion

Stages cross-fade and scale (0.5 s). Topic cards slide in from their own side, one after another (90 ms rhythm). The region
picker's camera glides between department, province and district. Charts draw in, numbers count. The field log opens like a ship log: a scan sweeps the screen while the line draws from 1998, the entries pop in one by one along their arrows, the coming year fades in last, and an entry rings once when it becomes the current one. Nothing loops except the sky,
the satellite, three comets that fall now and then, the campfire and Sprout's idle bob. Everything turns off with `prefers-reduced-motion`.

## 10. Two modes: Farmer and Pro

A switch in the top bar (`state.mode`, saved in the browser). Same NASA data, two ways to read it.

| | Farmer mode (default) | Pro mode |
|---|---|---|
| Readings | A **tool the farmer knows**, drawn in pixels: thermometer (heat), rain gauge (rain), a handful of soil — cracked, moist or puddled (soil wetness), a plant — bare, thirsty or healthy (greenness) — plus a **word** ("Hot", "A little rain") | The number with its unit and a sparkline |
| Rotation fit | A plant (healthy / thirsty / dead) and a word: Good fit · Could work · Poor fit | The score out of 100 |
| Comparison | An arrow and Better / Worse / Same | Five squares per topic and the arrow |
| Year by year | Warming stripes and three tangible facts ("About 4× the rain of a normal year") | The same plus the annual rain bars with the extreme years labeled |

Rules: Farmer mode never shows a percentage or a decimal; thresholds live in `levelWord()` (`web/src/content.js`), so the
science is the same in both modes. Sprout explains in words what the icons show.

## 11. Original charts we use

| Chart | Where | Why it is ours |
|---|---|---|
| Row of 12 plants | Rotations | A year read like a furrow: seed, growing, stressed, harvest, bare soil |
| Warming stripes | Year by year | One stripe per year from 1981, turquoise cooler → campfire hotter |
| One-story bars | Year by year (Pro) | Only the wettest year in `--fire` and the driest in `--sand` are lit |
| Pixel instruments | Signal panel (Farmer) | Thermometer and rain gauge fill up with the real value |
| Pixel globe | Signal panel | A small Earth (land from NASA GRACE's land mask) turns to the chosen place and marks it with a campfire pixel |
