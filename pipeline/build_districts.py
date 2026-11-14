"""Builds web/src/data/lambayeque_admin.json: the department, its 3 provinces and their districts, as small polygons.

Source: OpenStreetMap administrative boundaries (© OpenStreetMap contributors, ODbL), downloaded once with Overpass:

    curl -A "FieldShift" -H "Accept: application/json" -X POST https://overpass-api.de/api/interpreter --data-urlencode \
      'data=[out:json][timeout:90];area["ISO3166-2"="PE-LAM"]->.a;
      (relation["boundary"="administrative"]["admin_level"~"^(6|8)$"](area.a);relation["ISO3166-2"="PE-LAM"];);out geom;' -o osm.json

Usage: python build_districts.py osm.json ../web/src/data/lambayeque_admin.json
No dependencies. Rings are [lon, lat] pairs rounded to 4 decimals (~11 m), simplified to about 100 m.
"""
import json
import sys

TOLERANCE = 0.001   # degrees, about 110 m


def rings_of(relation):
    """Stitches the relation's outer ways into closed rings of (lon, lat)."""
    ways = [[(p["lon"], p["lat"]) for p in m["geometry"]] for m in relation["members"]
            if m["type"] == "way" and m.get("role") != "inner" and m.get("geometry")]
    rings = []
    while ways:
        ring = ways.pop()
        while ring[0] != ring[-1]:
            for i, w in enumerate(ways):
                if w[0] == ring[-1]:
                    ring += w[1:]
                elif w[-1] == ring[-1]:
                    ring += w[-2::-1]
                else:
                    continue
                ways.pop(i)
                break
            else:
                break   # open ring: the relation is broken in OSM
        if ring[0] == ring[-1] and len(ring) > 3:
            rings.append(ring)
    return rings


def simplify(pts, tol):
    """Douglas-Peucker, iterative. A closed ring is first split at the point farthest from its start."""
    keep = [False] * len(pts)
    keep[0] = keep[-1] = True
    far = max(range(len(pts)), key=lambda i: (pts[i][0] - pts[0][0]) ** 2 + (pts[i][1] - pts[0][1]) ** 2)
    keep[far] = True
    stack = [(0, far), (far, len(pts) - 1)]
    while stack:
        a, b = stack.pop()
        (x1, y1), (x2, y2) = pts[a], pts[b]
        dx, dy = x2 - x1, y2 - y1
        norm = (dx * dx + dy * dy) ** 0.5 or 1e-12
        worst, at = 0, None
        for i in range(a + 1, b):
            d = abs(dy * (pts[i][0] - x1) - dx * (pts[i][1] - y1)) / norm
            if d > worst:
                worst, at = d, i
        if at is not None and worst > tol:
            keep[at] = True
            stack += [(a, at), (at, b)]
    return [p for p, k in zip(pts, keep) if k]


def area(ring):
    return abs(sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(ring, ring[1:]))) / 2


def inside(pt, ring):
    x, y = pt
    hit = False
    for (x1, y1), (x2, y2) in zip(ring, ring[1:]):
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            hit = not hit
    return hit


def centroid(ring):
    a = cx = cy = 0
    for (x1, y1), (x2, y2) in zip(ring, ring[1:]):
        f = x1 * y2 - x2 * y1
        a += f
        cx += (x1 + x2) * f
        cy += (y1 + y2) * f
    return (cx / (3 * a), cy / (3 * a))


def shape(relation):
    rings = sorted(rings_of(relation), key=area, reverse=True)
    main = rings[0]
    out = [[[round(x, 4), round(y, 4)] for x, y in simplify(r, TOLERANCE)] for r in rings if area(r) > area(main) * 0.02]
    return main, out


def main(src, dst):
    els = json.load(open(src, encoding="utf-8"))["elements"]
    level = lambda n: [e for e in els if e["tags"].get("admin_level") == n]
    clean = lambda name: name.replace("Provincia de ", "").replace("Distrito de ", "").strip()
    dep_ring, dep_rings = shape(level("4")[0])
    provinces = []
    for p in level("6"):
        ring, rings = shape(p)
        if not inside(centroid(ring), dep_ring):
            continue   # a neighbouring province that only touches the border
        provinces.append({"name": clean(p["tags"]["name"]), "ring": ring, "rings": rings, "districts": []})
    for d in level("8"):
        ring, rings = shape(d)
        c = centroid(ring)
        home = next((p for p in provinces if inside(c, p["ring"])), None)
        if home:
            home["districts"].append({"name": clean(d["tags"]["name"]), "center": [round(c[0], 4), round(c[1], 4)], "rings": rings})
    for p in provinces:
        del p["ring"]
        p["districts"].sort(key=lambda d: d["name"])
    provinces.sort(key=lambda p: p["name"])
    out = {"source": "© OpenStreetMap contributors (ODbL), administrative boundaries", "department": {"name": "Lambayeque", "rings": dep_rings}, "provinces": provinces}
    json.dump(out, open(dst, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    for p in provinces:
        print(p["name"], len(p["districts"]), [d["name"] for d in p["districts"]])


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
