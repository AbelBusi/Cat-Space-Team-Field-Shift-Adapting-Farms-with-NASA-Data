# Lambayeque: the two risks we focus on

Phase 1 of the project is Lambayeque, Peru. The hackathon's local guide pointed to **El Niño** as a strong storyline, and
farmers here also fight **soil salinity** every season. This note says what we already show, with which NASA data, and what is next.

## 1. Coastal El Niño (in the app)

**What happens:** warm water off the Peruvian coast brings heavy rain to a desert that normally gets ~200 mm a year:
floods, washed-out fields, lost rice and maize, and then pests and diseases.

**What the data say (checked):**

| Fact | Source | Value |
|---|---|---|
| Typical rain at the Chiclayo cell | GPM IMERG 0.1°, 2001–2024 | 217 mm/year |
| Rain in 2017 (coastal El Niño) | GPM IMERG | **412 mm**, about 2× a normal year |
| Wettest year since 1981 | NASA POWER | **1998** (the 1997–98 El Niño), about 4× a normal year |
| Coastal El Niño years | NOAA Niño 1+2, Jan–Apr anomaly ≥ 0.8 °C | **1983, 1998, 2016, 2017, 2023** |
| Same years with NOAA's ONI (central Pacific) | IMERG | Chiclayo shows **less** rain than usual (187 mm): the wrong index for this coast |
| Right now | NOAA ONI | Aug–Oct 2026 = +2.46 °C: a strong El Niño is under way |

**In the app:** inside Lambayeque the "El Niño years" switch averages the coastal years above (Niño 1+2), not ONI. The rain layer,
the 0.1° rain grid on the map, the risk icons in the year rows and the "maize may flood" warning all follow it. Sprout explains
why this coast needs its own index.

**Next:** daily IMERG for extreme-rain days (how many days above 50 mm in a coastal El Niño), and the 2017 and 2023 events shown
on the map with GIBS IMERG imagery.

## 2. Soil salinity (planned)

**What happens:** in low, flat, poorly drained areas (Mórrope and parts of the lower Chancay–Lambayeque valley), irrigation water
evaporates and leaves salt in the topsoil. Flooded rice and a rising water table make it worse. Yields drop long before the salt
crust is visible.

**Honest limit:** **no NASA satellite measures soil salinity directly.** (SMAP and Aquarius salinity products are for the ocean.)
We can only combine indirect signs and say so on screen.

| Clue | Data | Status |
|---|---|---|
| Bright, bare, salt-crusted ground; weak vegetation inside irrigated land | HLS (Landsat/Sentinel-2) bands → salinity indices such as `SI = √(Blue × Red)` and `NDSI = (Red − NIR) / (Red + NIR)` | HLS ordered in AppEEARS (service was down) |
| Low, flat land where water and salt collect | NASADEM elevation and slope | **Already in the grid file** |
| Hot, stressed fields despite irrigation | ECOSTRESS LST and ET | Ordered in AppEEARS |
| Mapped saline soils (salinity / ECe classes) | FAO Harmonized World Soil Database v2.0, FAO Global Soil Salinity Map, GAEZ soil constraints | Not downloaded; **check licenses** first |
| Ground truth | Local soil tests (EC), agronomists in Mórrope | Ask the farmer: the confidence checklist already has "I have a recent soil test" |

**Crop salt tolerance** (threshold soil salinity before yield starts to fall, ECe in dS/m; FAO Irrigation and Drainage Paper 29,
after Maas & Hoffman, values to double-check in the source before showing them):

| Crop | Threshold ECe (dS/m) | Reading |
|---|---|---|
| Maize | ~1.7 | Moderately sensitive |
| Rice | ~3.0 | Moderately sensitive, but the flooded paddy can wash salt down |
| Cowpea | ~4.9 | Moderately tolerant |
| Sorghum | ~6.8 | Moderately tolerant |
| Cotton | ~7.7 | Tolerant |

**Plan for the app (small steps):**
1. Add a **"Salty soil"** priority card next to "Save water" (it reorders rotations like the others).
2. Give each crop its salt threshold in `content.js` and add salt tolerance to the rotation scores.
3. Mark grid cells that are **flat, low and near the coast** (from NASADEM) as "check for salt" in the Ground row, with Sprout
   saying it plainly: "This low, flat land can collect salt. A soil test (EC) will tell you."
4. When HLS arrives, add the salinity index as a map layer.
