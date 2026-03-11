#!/usr/bin/env python3
"""
fetch.py — Fetch restaurants from Google Places API.

Usage:
    python scripts/fetch.py --zip 91344
    python scripts/fetch.py --zip 91344 91343 91326
    python scripts/fetch.py --all

API key is read from env var GOOGLE_PLACES_KEY, or falls back to the hardcoded default.
"""

import argparse
import datetime
import glob
import json
import os
import time

import requests

API_KEY = os.environ.get("GOOGLE_PLACES_KEY", "AIzaSyCOMGtfqWl0CxG6jbwAyLjwzxdD9Ngq9aY")
DATA_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "data"))

# ── Zip fetch order (north-to-south, west-to-east) ────────────────────────────
ZIP_ORDER = [
    "91311",  # Chatsworth
    "91304",  # Canoga Park
    "91303",  # Canoga Park
    "91307",  # West Hills
    "91306",  # Winnetka
    "91326",  # Porter Ranch
    "91344",  # Granada Hills
    "91324",  # Northridge
    "91325",  # Northridge
    "91330",  # Northridge (CSUN)
    "91335",  # Reseda
    "91343",  # North Hills
    "91345",  # Mission Hills
    "91340",  # San Fernando
    "91342",  # Sylmar
    "91331",  # Pacoima
    "91352",  # Sun Valley
    "91364",  # Woodland Hills
    "91367",  # Woodland Hills
    "91356",  # Tarzana
    "91316",  # Encino
    "91436",  # Encino
    "91406",  # Van Nuys
    "91405",  # Van Nuys
    "91401",  # Van Nuys
    "91411",  # Van Nuys
    "91402",  # Panorama City
    "91423",  # Sherman Oaks
    "91403",  # Sherman Oaks
    "91501",  # Burbank
]

ZIP_CENTROIDS = {
    "91311": (34.2505, -118.6009),  # Chatsworth
    "91304": (34.2190, -118.6053),  # Canoga Park
    "91303": (34.2000, -118.5960),  # Canoga Park
    "91307": (34.1935, -118.6205),  # West Hills
    "91306": (34.2015, -118.5720),  # Winnetka
    "91326": (34.2561, -118.5498),  # Porter Ranch
    "91344": (34.2680, -118.4958),  # Granada Hills
    "91324": (34.2310, -118.5710),  # Northridge
    "91325": (34.2380, -118.5350),  # Northridge
    "91330": (34.2410, -118.5290),  # Northridge (CSUN)
    "91335": (34.2010, -118.5360),  # Reseda
    "91343": (34.2352, -118.4677),  # North Hills
    "91345": (34.2479, -118.4533),  # Mission Hills
    "91340": (34.2435, -118.4377),  # San Fernando
    "91342": (34.2608, -118.4256),  # Sylmar
    "91331": (34.2380, -118.3731),  # Pacoima
    "91352": (34.2205, -118.3892),  # Sun Valley
    "91364": (34.1680, -118.5990),  # Woodland Hills
    "91367": (34.1870, -118.5805),  # Woodland Hills
    "91356": (34.1745, -118.5612),  # Tarzana
    "91316": (34.1670, -118.5237),  # Encino
    "91436": (34.1510, -118.4868),  # Encino
    "91406": (34.1945, -118.4525),  # Van Nuys
    "91405": (34.1970, -118.4277),  # Van Nuys
    "91401": (34.1828, -118.4025),  # Van Nuys
    "91411": (34.1760, -118.4440),  # Van Nuys
    "91402": (34.2163, -118.4266),  # Panorama City
    "91423": (34.1539, -118.4362),  # Sherman Oaks
    "91403": (34.1475, -118.4603),  # Sherman Oaks
    "91501": (34.1815, -118.3038),  # Burbank
}

# ── Chain blocklist ────────────────────────────────────────────────────────────
CHAIN_BLOCKLIST = {
    "7-eleven", "circle k", "am/pm", "ampm",
    "mcdonald", "burger king", "wendy's", "wendys", "jack in the box",
    "in-n-out", "five guys", "shake shack", "fatburger", "habit burger",
    "the habit", "carl's jr", "carls jr", "hardee's", "whataburger",
    "sonic drive", "rally's", "checkers",
    "kfc", "chick-fil-a", "popeyes", "raising cane", "wingstop",
    "el pollo loco", "church's chicken", "zaxby's", "dave's hot chicken",
    "taco bell", "del taco", "chipotle", "qdoba", "moe's southwest",
    "baja fresh", "taco john",
    "domino's", "dominoes", "pizza hut", "little caesar", "papa john", "papa murphy",
    "subway", "quiznos", "jersey mike", "firehouse subs", "jimmy john", "potbelly", "which wich",
    "panda express", "pei wei", "yoshinoya", "waba grill",
    "panera", "jason's deli", "corner bakery", "noodles & company", "zoes kitchen",
    "starbucks", "dunkin'", "dunkin donuts", "dutch bros", "peet's coffee", "peets coffee",
    "denny's", "dennys", "ihop", "perkins", "waffle house", "coco's", "sizzler",
    "golden corral", "hometown buffet", "old country buffet",
    "applebee's", "applebees", "chili's", "chilis", "tgi friday", "red lobster",
    "olive garden", "buffalo wild wings", "bj's restaurant", "cheesecake factory",
    "p.f. chang", "pf chang", "benihana", "outback steakhouse", "red robin",
    "bob evans", "cracker barrel",
    "robeks", "jamba juice", "smoothie king", "tropical smoothie",
    "nothing bundt", "cold stone", "baskin-robbins", "baskin robbins",
    "dairy queen", "orange julius",
}

TYPE_TO_CUISINE = {
    "vietnamese_restaurant": ["vietnamese"],
    "mexican_restaurant": ["mexican"],
    "pizza_restaurant": ["pizza"],
    "italian_restaurant": ["italian"],
    "chinese_restaurant": ["chinese"],
    "japanese_restaurant": ["japanese"],
    "korean_restaurant": ["korean"],
    "thai_restaurant": ["thai"],
    "indian_restaurant": ["indian"],
    "mediterranean_restaurant": ["mediterranean"],
    "greek_restaurant": ["greek"],
    "american_restaurant": ["american"],
    "hamburger_restaurant": ["burgers"],
    "sandwich_shop": ["sandwiches"],
    "seafood_restaurant": ["seafood"],
    "steak_house": ["steakhouse"],
    "sushi_restaurant": ["sushi", "japanese"],
    "ramen_restaurant": ["ramen", "japanese"],
    "barbecue_restaurant": ["bbq"],
    "breakfast_restaurant": ["diner"],
    "brunch_restaurant": ["diner"],
    "bakery": ["bakery"],
    "cafe": ["cafe"],
    "dessert_shop": ["dessert"],
    "ice_cream_shop": ["dessert"],
    "middle_eastern_restaurant": ["mediterranean"],
    "filipino_restaurant": ["filipino"],
    "peruvian_restaurant": ["peruvian"],
    "salvadoran_restaurant": ["salvadoran"],
    "guatemalan_restaurant": ["guatemalan"],
}

TYPE_TO_VIBE = {
    "fast_food_restaurant": ["fast-food"],
    "fast_casual_restaurant": ["fast-casual"],
    "food_truck": ["food-truck"],
    "bar": ["bar-scene"],
    "coffee_shop": ["cafe"],
    "diner": ["casual", "diner"],
    "buffet_restaurant": ["buffet"],
    "brunch_restaurant": ["brunch"],
    "breakfast_restaurant": ["breakfast"],
    "drive_through": ["drive-thru"],
}


def is_chain(name):
    lower = name.lower()
    return any(c in lower for c in CHAIN_BLOCKLIST)


def map_types_to_tags(types):
    cuisine, vibe = [], []
    for t in types:
        cuisine.extend(TYPE_TO_CUISINE.get(t, []))
        vibe.extend(TYPE_TO_VIBE.get(t, []))
    return list(dict.fromkeys(cuisine)), list(dict.fromkeys(vibe))


def map_price(price_level):
    if price_level is None:
        return None
    if price_level <= 1:
        return "cheap"
    elif price_level == 2:
        return "mid"
    return "upscale"


def _price_level_new(price_str):
    mapping = {
        "PRICE_LEVEL_FREE": 0,
        "PRICE_LEVEL_INEXPENSIVE": 1,
        "PRICE_LEVEL_MODERATE": 2,
        "PRICE_LEVEL_EXPENSIVE": 3,
        "PRICE_LEVEL_VERY_EXPENSIVE": 4,
    }
    return mapping.get(price_str)


def get_tile_centers(zip_code):
    lat, lng = ZIP_CENTROIDS[zip_code]
    offsets = [-0.018, -0.009, 0.0, 0.009, 0.018]
    return [(lat + dlat, lng + dlng) for dlat in offsets for dlng in offsets]


def fetch_tile(lat, lng, radius=800):
    url = "https://places.googleapis.com/v1/places:searchNearby"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": API_KEY,
        "X-Goog-FieldMask": (
            "places.id,places.displayName,places.formattedAddress,"
            "places.location,places.rating,places.userRatingCount,"
            "places.priceLevel,places.types,places.primaryType"
        ),
    }
    body = {
        "includedTypes": ["restaurant"],
        "maxResultCount": 20,
        "locationRestriction": {
            "circle": {
                "center": {"latitude": lat, "longitude": lng},
                "radius": float(radius),
            }
        },
    }
    resp = requests.post(url, json=body, headers=headers, timeout=30)
    resp.raise_for_status()
    results = []
    for p in resp.json().get("places", []):
        loc = p.get("location", {})
        results.append({
            "place_id": p.get("id", ""),
            "name": p.get("displayName", {}).get("text", ""),
            "vicinity": p.get("formattedAddress", ""),
            "lat": loc.get("latitude"),
            "lng": loc.get("longitude"),
            "rating": p.get("rating"),
            "user_ratings_total": p.get("userRatingCount"),
            "price_level": _price_level_new(p.get("priceLevel")),
            "types": p.get("types", []),
            "primary_type": p.get("primaryType", ""),
        })
    return results


def fetch_place_website(place_id):
    url = "https://maps.googleapis.com/maps/api/place/details/json"
    params = {"place_id": place_id, "fields": "website", "key": API_KEY}
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json().get("result", {}).get("website")


def build_entry(place, zip_code):
    primary = place.get("primary_type", "")
    all_types = list(dict.fromkeys([primary] + place.get("types", []))) if primary else place.get("types", [])
    cuisine, vibe = map_types_to_tags(all_types)
    return {
        "id": place["place_id"],
        "name": place.get("name", ""),
        "address": place.get("vicinity", ""),
        "zip": zip_code,
        "neighborhood": "",
        "lat": place.get("lat"),
        "lng": place.get("lng"),
        "google_rating": place.get("rating"),
        "google_count": place.get("user_ratings_total"),
        "status": "pending",
        "exclude_reason": None,
        "cuisine": cuisine,
        "price": map_price(place.get("price_level")),
        "vibe": vibe,
        "dishes": [],
        "personal_rating": None,
        "personal_notes": None,
        "website": place.get("_website"),
        "added": datetime.date.today().isoformat(),
    }


def load_existing_ids(exclude_zips=None):
    """Return set of place IDs from all existing per-zip JSONs, excluding specified zips."""
    exclude_zips = set(exclude_zips or [])
    seen = set()
    for path in glob.glob(os.path.join(DATA_DIR, "restaurants-*.json")):
        base = os.path.basename(path)
        if base == "restaurants-all.json":
            continue
        zip_code = base.replace("restaurants-", "").replace(".json", "")
        if zip_code in exclude_zips:
            continue
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            for r in data.get("restaurants", []):
                seen.add(r["id"])
        except Exception as e:
            print(f"  Warning: could not read {path}: {e}")
    return seen


def load_existing_zip(zip_code):
    """Load existing per-zip JSON. Returns dict of id→entry."""
    path = os.path.join(DATA_DIR, f"restaurants-{zip_code}.json")
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return {r["id"]: r for r in data.get("restaurants", [])}


def fetch_zip(zip_code, global_seen):
    """
    Fetch restaurants for one zip. Updates global_seen in place with newly kept IDs.
    - Places owned by other zips (in global_seen) are skipped.
    - Places already in this zip's JSON are refreshed (google_rating, google_count, address).
    - Brand-new places are added with status: pending.
    """
    print(f"\n[{zip_code}] Fetching...")
    existing = load_existing_zip(zip_code)
    tiles = get_tile_centers(zip_code)

    tile_seen = set()
    to_update = []   # places already owned by this zip
    raw_new = []     # brand-new places

    for i, (lat, lng) in enumerate(tiles):
        print(f"  Tile {i+1}/{len(tiles)} ({lat:.4f}, {lng:.4f}) ...", end=" ", flush=True)
        places = fetch_tile(lat, lng)
        n_dup = n_chain = n_global = n_own = n_new = 0

        for p in places:
            pid = p["place_id"]
            if pid in tile_seen:
                n_dup += 1
                continue
            tile_seen.add(pid)
            if is_chain(p["name"]):
                n_chain += 1
                continue
            if pid in global_seen:
                n_global += 1
                continue
            if pid in existing:
                to_update.append(p)
                n_own += 1
            else:
                raw_new.append(p)
                n_new += 1

        print(f"{len(places)} found, {n_new} new, {n_own} updating, "
              f"{n_chain} chains, {n_global} global-dup, {n_dup} tile-dup")
        time.sleep(0.5)

    # Fetch website for brand-new places only
    if raw_new:
        print(f"  Fetching website details for {len(raw_new)} new places...")
        for i, place in enumerate(raw_new):
            try:
                place["_website"] = fetch_place_website(place["place_id"])
            except Exception as e:
                print(f"    Warning: details failed for {place['name']}: {e}")
                place["_website"] = None
            time.sleep(0.3)
            if (i + 1) % 10 == 0:
                print(f"    {i+1}/{len(raw_new)} done")

    # Build result: start from existing, apply updates, add new entries
    result = dict(existing)

    # Update google fields on re-fetched existing entries
    for place in to_update:
        pid = place["place_id"]
        entry = result[pid]
        entry["google_rating"] = place.get("rating")
        entry["google_count"] = place.get("user_ratings_total")
        entry["address"] = place.get("vicinity", entry["address"])

    # Add new entries
    for place in raw_new:
        entry = build_entry(place, zip_code)
        result[entry["id"]] = entry

    # Register all this zip's IDs in global_seen
    for pid in result:
        global_seen.add(pid)

    restaurants = sorted(result.values(), key=lambda r: r["name"].lower())

    os.makedirs(DATA_DIR, exist_ok=True)
    out_path = os.path.join(DATA_DIR, f"restaurants-{zip_code}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(
            {"meta": {"zip": zip_code, "generated": datetime.date.today().isoformat()},
             "restaurants": restaurants},
            f, indent=2, ensure_ascii=False,
        )

    n_new_total = len(raw_new)
    n_updated = len(to_update)
    print(f"  Saved {len(restaurants)} total ({n_new_total} new, {n_updated} updated) "
          f"-> restaurants-{zip_code}.json")


def main():
    parser = argparse.ArgumentParser(description="Fetch restaurants from Google Places API.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--zip", nargs="+", metavar="ZIP", help="Zip code(s) to fetch")
    group.add_argument("--all", action="store_true", help="Fetch all zips in ZIP_ORDER")
    args = parser.parse_args()

    if args.all:
        zips_to_fetch = list(ZIP_ORDER)
    else:
        for z in args.zip:
            if z not in ZIP_CENTROIDS:
                print(f"Error: No centroid defined for zip {z}. Add it to ZIP_CENTROIDS.")
                raise SystemExit(1)
        order_map = {z: i for i, z in enumerate(ZIP_ORDER)}
        zips_to_fetch = sorted(args.zip, key=lambda z: order_map.get(z, 999))

    # Load IDs owned by zips NOT being fetched this run (cross-zip dedup)
    global_seen = load_existing_ids(exclude_zips=zips_to_fetch)
    print(f"Loaded {len(global_seen)} existing IDs from other zips (dedup fence)")

    for zip_code in zips_to_fetch:
        fetch_zip(zip_code, global_seen)

    print("\nAll done.")


if __name__ == "__main__":
    main()
