#!/usr/bin/env python3
"""
fetch_restaurants.py

Fetches restaurants in a given zip code from Google Places API (Nearby Search).
Uses a 3x3 tile grid centered on the zip centroid to maximize coverage.
Deduplicates by Place ID. Outputs a structured JSON file.

Usage:
    python scripts/fetch_restaurants.py --zip 91344 --key YOUR_GOOGLE_API_KEY
    python scripts/fetch_restaurants.py --zip 91344 --key YOUR_KEY --out data/restaurants-91344.json

Requirements:
    pip install requests
"""

import argparse
import json
import os
import time
import datetime
import requests


# ── Zip centroid map ───────────────────────────────────────────────────────────
# Add more zip codes here for SFV expansion.
ZIP_CENTROIDS = {
    "91344": (34.2680, -118.4958),  # Granada Hills
    "91343": (34.2352, -118.4677),  # North Hills
    "91326": (34.2561, -118.5498),  # Porter Ranch
    "91340": (34.2435, -118.4377),  # San Fernando
    "91342": (34.2608, -118.4256),  # Sylmar
    "91345": (34.2479, -118.4533),  # Mission Hills
    "91402": (34.2163, -118.4266),  # Panorama City
    "91401": (34.1828, -118.4025),  # Van Nuys
    "91405": (34.1970, -118.4277),  # Van Nuys
    "91406": (34.1945, -118.4525),  # Van Nuys
    "91411": (34.1760, -118.4440),  # Van Nuys
    "91352": (34.2205, -118.3892),  # Sun Valley
    "91331": (34.2380, -118.3731),  # Pacoima
    "91335": (34.2010, -118.5360),  # Reseda
    "91356": (34.1745, -118.5612),  # Tarzana
    "91367": (34.1870, -118.5805),  # Woodland Hills
    "91364": (34.1680, -118.5990),  # Woodland Hills
    "91307": (34.1935, -118.6205),  # West Hills
    "91304": (34.2190, -118.6053),  # Canoga Park
    "91303": (34.2000, -118.5960),  # Canoga Park
    "91306": (34.2015, -118.5720),  # Winnetka
    "91311": (34.2505, -118.6009),  # Chatsworth
    "91324": (34.2310, -118.5710),  # Northridge
    "91325": (34.2380, -118.5350),  # Northridge
    "91330": (34.2410, -118.5290),  # Northridge (CSUN)
    "91436": (34.1510, -118.4868),  # Encino
    "91316": (34.1670, -118.5237),  # Encino
    "91423": (34.1539, -118.4362),  # Sherman Oaks
    "91403": (34.1475, -118.4603),  # Sherman Oaks
    "91501": (34.1815, -118.3038),  # Burbank
}

# ── Google type → taxonomy mapping ────────────────────────────────────────────
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


def map_types_to_tags(types):
    """Convert Google place types list to (cuisine[], vibe[]) taxonomy tags."""
    cuisine = []
    vibe = []
    for t in types:
        cuisine.extend(TYPE_TO_CUISINE.get(t, []))
        vibe.extend(TYPE_TO_VIBE.get(t, []))
    # Deduplicate while preserving order
    cuisine = list(dict.fromkeys(cuisine))
    vibe = list(dict.fromkeys(vibe))
    return cuisine, vibe


def map_price(price_level):
    """Google price_level (0–4) → taxonomy price string."""
    if price_level is None:
        return None
    if price_level <= 1:
        return "cheap"
    elif price_level == 2:
        return "mid"
    else:
        return "upscale"


def get_tile_centers(zip_code):
    """
    Returns 25 (lat, lng) tile centers for a 5x5 grid covering a zip code area.
    Tiles are spaced ~0.009 degrees apart (~1km) with 800m radius per tile.
    25 tiles × 20 results = 500 max before dedup, giving dense coverage.
    """
    lat, lng = ZIP_CENTROIDS[zip_code]
    offsets = [-0.018, -0.009, 0.0, 0.009, 0.018]
    centers = []
    for dlat in offsets:
        for dlng in offsets:
            centers.append((lat + dlat, lng + dlng))
    return centers


def fetch_all_for_tile(api_key, lat, lng, radius=800):
    """
    Fetches up to 20 restaurant results for one tile using Places API (New).
    The new API has no pagination — max 20 results per request.
    Returns list of raw place dicts normalized for build_restaurant_entry.
    """
    url = "https://places.googleapis.com/v1/places:searchNearby"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": (
            "places.id,places.displayName,places.formattedAddress,"
            "places.location,places.rating,places.userRatingCount,"
            "places.priceLevel,places.types,places.primaryType,"
            "places.businessStatus"
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
    data = resp.json()

    results = []
    for p in data.get("places", []):
        loc = p.get("location", {})
        results.append({
            "place_id": p.get("id", ""),
            "name": p.get("displayName", {}).get("text", ""),
            "vicinity": p.get("formattedAddress", ""),
            "geometry": {"location": {"lat": loc.get("latitude"), "lng": loc.get("longitude")}},
            "rating": p.get("rating"),
            "user_ratings_total": p.get("userRatingCount"),
            "price_level": _price_level_new(p.get("priceLevel")),
            "types": p.get("types", []),
            "primary_type": p.get("primaryType", ""),
        })

    return results


def _price_level_new(price_str):
    """Convert new API price level strings to integer (0–4) for map_price()."""
    mapping = {
        "PRICE_LEVEL_FREE": 0,
        "PRICE_LEVEL_INEXPENSIVE": 1,
        "PRICE_LEVEL_MODERATE": 2,
        "PRICE_LEVEL_EXPENSIVE": 3,
        "PRICE_LEVEL_VERY_EXPENSIVE": 4,
    }
    return mapping.get(price_str)


def fetch_place_details(api_key, place_id):
    """Fetch extra details (website, formatted_phone_number) for one place."""
    url = "https://maps.googleapis.com/maps/api/place/details/json"
    params = {
        "place_id": place_id,
        "fields": "website,formatted_phone_number",
        "key": api_key,
    }
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    time.sleep(0.3)
    data = resp.json()
    result = data.get("result", {})
    return {
        "website": result.get("website"),
        "phone": result.get("formatted_phone_number"),
    }


def fetch_all_for_zip(api_key, zip_code, fetch_details=True):
    """
    Fetches all unique restaurants for a zip code using a 3x3 tile grid.
    Deduplicates by Google Place ID.
    Returns list of raw place dicts with optional extra detail fields.
    """
    tiles = get_tile_centers(zip_code)
    seen_ids = set()
    all_places = []

    n = len(tiles)
    for i, (lat, lng) in enumerate(tiles):
        print(f"  Tile {i+1}/{n} ({lat:.4f}, {lng:.4f}) ...", end=" ", flush=True)
        places = fetch_all_for_tile(api_key, lat, lng)
        new = [p for p in places if p["place_id"] not in seen_ids]
        for p in new:
            seen_ids.add(p["place_id"])
        all_places.extend(new)
        print(f"{len(places)} found, {len(new)} new (total: {len(all_places)})")
        time.sleep(0.5)

    if fetch_details:
        print(f"  Fetching details for {len(all_places)} places...")
        for i, place in enumerate(all_places):
            details = fetch_place_details(api_key, place["place_id"])
            place["_website"] = details.get("website")
            place["_phone"] = details.get("phone")
            if (i + 1) % 10 == 0:
                print(f"    {i+1}/{len(all_places)} details fetched")

    return all_places


def build_restaurant_entry(place, zip_code):
    """Build a full schema entry from a raw Google Places dict."""
    types = place.get("types", [])
    # Also include primaryType so it gets picked up by the mapping
    primary = place.get("primary_type", "")
    all_types = list(dict.fromkeys([primary] + types)) if primary else types
    cuisine, vibe = map_types_to_tags(all_types)
    price = map_price(place.get("price_level"))

    # Extract address components
    address = place.get("vicinity", "")

    # Geometry
    loc = place.get("geometry", {}).get("location", {})
    lat = loc.get("lat")
    lng = loc.get("lng")

    # Ratings
    google_rating = place.get("rating")
    google_count = place.get("user_ratings_total")

    today = datetime.date.today().isoformat()
    today_display = datetime.date.today().strftime("%b %Y").lower()

    tags = {
        "cuisine": cuisine,
        "price": price,
        "vibe": vibe,
        "dishes": [],
    }

    return {
        "id": place["place_id"],
        "name": place.get("name", ""),
        "address": address,
        "zip": zip_code,
        "neighborhood": "",  # Fill in manually or via geocoding
        "lat": lat,
        "lng": lng,
        "tags": tags,
        "ratings": {
            "google_rating": google_rating,
            "google_count": google_count,
            "personal_rating": None,
            "personal_notes": None,
        },
        "menu_items": [],
        "enrichment": {
            "menu_url": None,
            "menu_fetched": False,
            "menu_fetched_date": None,
            "reviews_fetched": False,
            "manually_verified": False,
        },
        "meta": {
            "added": today_display,
            "last_updated": today,
            "google_types": all_types,
            "website": place.get("_website"),
        },
    }


def main():
    parser = argparse.ArgumentParser(
        description="Fetch restaurants for a zip code from Google Places API."
    )
    parser.add_argument("--zip", required=True, help="Zip code to fetch (e.g. 91344)")
    parser.add_argument("--key", required=True, help="Google Places API key")
    parser.add_argument(
        "--out",
        default=None,
        help="Output JSON path (default: data/restaurants-{zip}.json)",
    )
    parser.add_argument(
        "--no-details",
        action="store_true",
        help="Skip the per-place Details API call (faster, no website data)",
    )
    args = parser.parse_args()

    zip_code = args.zip
    if zip_code not in ZIP_CENTROIDS:
        print(f"Error: No centroid defined for zip {zip_code}.")
        print(f"Add it to ZIP_CENTROIDS in this script.")
        raise SystemExit(1)

    out_path = args.out
    if out_path is None:
        out_path = os.path.join(
            os.path.dirname(__file__), "..", "data", f"restaurants-{zip_code}.json"
        )
    out_path = os.path.normpath(out_path)

    print(f"Fetching restaurants for zip {zip_code}...")
    places = fetch_all_for_zip(args.key, zip_code, fetch_details=not args.no_details)

    print(f"\nBuilding {len(places)} restaurant entries...")
    restaurants = [build_restaurant_entry(p, zip_code) for p in places]

    # Sort by name for stable output
    restaurants.sort(key=lambda r: r["name"].lower())

    output = {
        "meta": {
            "version": 1,
            "generated": datetime.date.today().isoformat(),
            "zips_included": [zip_code],
        },
        "restaurants": restaurants,
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\nDone. {len(restaurants)} restaurants written to {out_path}")

    # Quick tag summary
    cuisines = {}
    for r in restaurants:
        for c in r["tags"]["cuisine"]:
            cuisines[c] = cuisines.get(c, 0) + 1
    if cuisines:
        top = sorted(cuisines.items(), key=lambda x: -x[1])[:10]
        print("\nTop cuisines found:")
        for cuisine, count in top:
            print(f"  {cuisine}: {count}")


if __name__ == "__main__":
    main()
