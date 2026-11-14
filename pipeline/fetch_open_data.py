"""Downloads every open dataset (no login) for the places in data/places.csv into data/.

    python pipeline/fetch_open_data.py            # everything
    python pipeline/fetch_open_data.py power      # only one source: power | ndvi | soil | oni

Sources: NASA POWER (monthly 2001-2024), MODIS NDVI via ORNL DAAC (2024, slow: ~1 min per place),
ISRIC SoilGrids (topsoil), NOAA Oceanic Nino Index. Datasets that need an Earthdata login are listed in data/README.md.
"""
import concurrent.futures
import csv
import json
import pathlib
import sys
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"


def get(url, timeout=120):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return r.read()
    except (urllib.error.URLError, TimeoutError) as e:
        raise RuntimeError(f"{url[:90]}... failed: {e}") from e


def places():
    with open(DATA / "places.csv", newline="") as f:
        return [{"id": r["ID"], "lat": float(r["Latitude"]), "lon": float(r["Longitude"])} for r in csv.DictReader(f)]


def power(p):
    # Everything needed for heat, frost, rain, soil wetness and crop water demand (ET0).
    params = "T2M,T2M_MAX,T2M_MIN,T2M_RANGE,PRECTOTCORR,GWETTOP,GWETROOT,ALLSKY_SFC_SW_DWN,RH2M,WS2M"
    url = (f"https://power.larc.nasa.gov/api/temporal/monthly/point?parameters={params}&community=AG"
           f"&latitude={p['lat']}&longitude={p['lon']}&start=2001&end=2024&format=JSON")
    return json.loads(get(url))


def ndvi(p):
    out = []
    for a, b in [("A2024001", "A2024145"), ("A2024161", "A2024305"), ("A2024321", "A2024353")]:  # 10 images max per call
        url = (f"https://modis.ornl.gov/rst/api/v1/MOD13Q1/subset?latitude={p['lat']}&longitude={p['lon']}"
               f"&band=250m_16_days_NDVI&startDate={a}&endDate={b}&kmAboveBelow=0&kmLeftRight=0")
        out += [{"date": s["calendar_date"], "ndvi": None if s["data"][0] <= -2000 else round(s["data"][0] * 0.0001, 4)}
                for s in json.loads(get(url, timeout=300))["subset"]]
    return {"product": "MOD13Q1 v061, 250 m, 16-day", "source": "ORNL DAAC MODIS subsets", "values": out}


def soil(p):
    props = "".join(f"&property={k}" for k in ("clay", "sand", "silt", "soc", "phh2o", "bdod", "nitrogen"))
    depths = "".join(f"&depth={d}" for d in ("0-5cm", "5-15cm", "15-30cm"))
    return json.loads(get(f"https://rest.isric.org/soilgrids/v2.0/properties/query?lon={p['lon']}&lat={p['lat']}{props}{depths}&value=mean"))


SOURCES = {"power": power, "ndvi": ndvi, "soil": soil}


def run(name, fn):
    folder = DATA / name
    folder.mkdir(exist_ok=True)

    def one(p):
        try:
            (folder / f"{p['id']}.json").write_text(json.dumps(fn(p), indent=1))
            return f"  ok   {name}/{p['id']}.json"
        except Exception as e:  # keep going: one slow service must not stop the rest
            return f"  FAIL {name}/{p['id']}: {e}"

    print(f"{name}:")
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:  # be gentle with free public services
        for line in pool.map(one, places()):
            print(line, flush=True)


def oni():
    (DATA / "oni.txt").write_bytes(get("https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt"))
    print("oni:\n  ok   oni.txt")


if __name__ == "__main__":
    wanted = sys.argv[1:] or ["power", "soil", "oni", "ndvi"]
    for name in wanted:
        if name == "oni":
            oni()
        elif name in SOURCES:
            run(name, SOURCES[name])
        else:
            sys.exit(f"Unknown source {name!r}. Use: power ndvi soil oni")
