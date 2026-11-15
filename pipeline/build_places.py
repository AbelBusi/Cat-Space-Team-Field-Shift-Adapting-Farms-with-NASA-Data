"""Builds web/src/data/lambayeque_places.json: city, town and village names to label the satellite map.

Source: OpenStreetMap place nodes (© OpenStreetMap contributors, ODbL), downloaded once with Overpass:

    curl -A "FieldShift" -H "Accept: application/json" -X POST https://overpass-api.de/api/interpreter --data-urlencode \
      'data=[out:json][timeout:90];area["ISO3166-2"="PE-LAM"]->.a;
      node["place"~"^(city|town|village|hamlet|suburb)$"]["name"](area.a);out;' -o places.json

Usage: python build_places.py places.json ../web/src/data/lambayeque_places.json
Each place is [name, lat, lon, rank]; rank 0 = city, 1 = town, 2 = suburb, 3 = village, 4 = hamlet.
"""
import json
import sys

RANK = {"city": 0, "town": 1, "suburb": 2, "village": 3, "hamlet": 4}

els = json.load(open(sys.argv[1], encoding="utf-8"))["elements"]
places = sorted(([e["tags"]["name"], round(e["lat"], 4), round(e["lon"], 4), RANK[e["tags"]["place"]]] for e in els), key=lambda p: (p[3], p[0]))
json.dump(places, open(sys.argv[2], "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print(len(places), "places")
