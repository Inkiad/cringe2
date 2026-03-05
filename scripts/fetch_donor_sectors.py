#!/usr/bin/env python3
"""
fetch_donor_sectors.py

Fetches campaign donor sector breakdowns for CA state senators and assembly
members from the FollowTheMoney API.

Outputs: data/ca-donor-sectors.json

Usage:
    python scripts/fetch_donor_sectors.py [--senate-only] [--assembly-only]

Requirements:
    pip install requests
"""

import requests
import json
import time
import os
import sys

API_KEY = os.environ.get("FTM_API_KEY", "4029c559ca16c0f7947110867b5d55b2")
BASE_URL = "https://api.followthemoney.org/"

# CA Senate: staggered terms. Even districts ran in 2022, odd in 2024.
# office_id is FTM's internal ID for each district's seat.
# These were confirmed by querying &s=CA&y=2024&gro=c-r-osid and y=2022.
STATE_SENATE_OFFICES = {
    "1":  {"office_id": "670", "year": 2024},
    "2":  {"office_id": "671", "year": 2022},
    "3":  {"office_id": "672", "year": 2024},
    "4":  {"office_id": "673", "year": 2022},
    "5":  {"office_id": "674", "year": 2024},
    "6":  {"office_id": "675", "year": 2022},
    "7":  {"office_id": "676", "year": 2024},
    "8":  {"office_id": "677", "year": 2022},
    "9":  {"office_id": "678", "year": 2024},
    "10": {"office_id": "679", "year": 2022},
    "11": {"office_id": "680", "year": 2024},
    "12": {"office_id": "681", "year": 2022},
    "13": {"office_id": "682", "year": 2024},
    "14": {"office_id": "683", "year": 2022},
    "15": {"office_id": "684", "year": 2024},
    "16": {"office_id": "685", "year": 2022},
    "17": {"office_id": "686", "year": 2024},
    "18": {"office_id": "687", "year": 2022},
    "19": {"office_id": "688", "year": 2024},
    "20": {"office_id": "689", "year": 2022},
    "21": {"office_id": "690", "year": 2024},
    "22": {"office_id": "691", "year": 2022},
    "23": {"office_id": "692", "year": 2024},
    "24": {"office_id": "693", "year": 2022},
    "25": {"office_id": "694", "year": 2024},
    "26": {"office_id": "695", "year": 2022},
    "27": {"office_id": "696", "year": 2024},
    "28": {"office_id": "697", "year": 2022},
    "29": {"office_id": "698", "year": 2024},
    "30": {"office_id": "699", "year": 2022},
    "31": {"office_id": "700", "year": 2024},
    "32": {"office_id": "701", "year": 2022},
    "33": {"office_id": "702", "year": 2024},
    "34": {"office_id": "703", "year": 2022},
    "35": {"office_id": "704", "year": 2024},
    "36": {"office_id": "705", "year": 2022},
    "37": {"office_id": "706", "year": 2024},
    "38": {"office_id": "707", "year": 2022},
    "39": {"office_id": "708", "year": 2024},
    "40": {"office_id": "709", "year": 2022},
}

# Sectors to exclude from the output (noise / not informative)
EXCLUDE_SECTORS = {"Uncoded", "Unitemized Contributions", "Candidate Contributions"}


def ftm_get(params, retries=4):
    p = {"mode": "json", "APIKey": API_KEY, "recs": 200, **params}
    for attempt in range(retries):
        resp = requests.get(BASE_URL, params=p, timeout=60)
        resp.raise_for_status()
        if resp.content:
            time.sleep(0.6)
            return resp.json()
        # Empty body — back off and retry
        wait = 2 ** attempt
        print(f"(empty response, retrying in {wait}s)", end=" ", flush=True)
        time.sleep(wait)
    raise RuntimeError(f"API returned empty body after {retries} retries: {p}")


def try_ftm_get(params):
    """Like ftm_get but returns None on empty response instead of raising."""
    p = {"mode": "json", "APIKey": API_KEY, "recs": 200, **params}
    for attempt in range(3):
        resp = requests.get(BASE_URL, params=p, timeout=60)
        resp.raise_for_status()
        if resp.content:
            time.sleep(0.6)
            return resp.json()
        time.sleep(2 ** attempt)
    return None


def parse_sectors(records):
    sectors = []
    for r in records:
        if not isinstance(r, dict):
            continue
        sector = r.get("Broad_Sector", {}).get("Broad_Sector", "")
        total  = float(r.get("Total_$", {}).get("Total_$", 0) or 0)
        if sector and sector not in EXCLUDE_SECTORS and total > 0:
            sectors.append({"sector": sector, "total": int(total)})
    sectors.sort(key=lambda x: x["total"], reverse=True)
    return sectors


def get_winner_and_sectors(office_id, year):
    """
    Returns (candidate_name, total, sectors) for the winning candidate.
    Falls back to office-level sector aggregation when candidate lookup fails
    (some offices don't support gro=c-t-id — contributions are still queryable
    at the office level, which is fine for uncontested/safe races).
    """
    # Step 1: try to identify the winning candidate
    data = try_ftm_get({"s": "CA", "y": year, "c-r-osid": office_id, "gro": "c-t-id"})
    cid, name, total = None, None, None
    if data:
        records = [r for r in data.get("records", []) if isinstance(r, dict)]
        if records:
            winners = [r for r in records if r.get("Status_of_Candidate", {}).get("Status_of_Candidate") == "Won"]
            best = max(winners or records, key=lambda r: float(r.get("Total_$", {}).get("Total_$", 0) or 0))
            cid   = best.get("Candidate", {}).get("id")
            name  = best.get("Candidate", {}).get("Candidate", "")
            total = float(best.get("Total_$", {}).get("Total_$", 0) or 0)

    # Step 2: get sector breakdown — per candidate if we have a cid, else per office
    if cid:
        sector_data = try_ftm_get({"s": "CA", "y": year, "c-t-id": cid, "gro": "d-ccg"})
    else:
        sector_data = try_ftm_get({"y": year, "c-r-osid": office_id, "gro": "d-ccg"})

    if not sector_data:
        return name, total, []

    sectors = parse_sectors(sector_data.get("records", []))

    # If we used office-level fallback, derive total from sectors
    if not total:
        total = sum(s["total"] for s in sectors)

    return name, total, sectors


def fetch_chamber(office_map, label):
    output = {}
    districts = sorted(office_map.keys(), key=int)
    print(f"\nFetching {label} ({len(districts)} districts)...")

    for dist in districts:
        info = office_map[dist]
        office_id = info["office_id"]
        year = info["year"]

        print(f"  {label} {dist} (office {office_id}, {year}) ...", end=" ", flush=True)

        name, total, sectors = get_winner_and_sectors(office_id, year)
        if not sectors:
            print("no data")
            output[dist] = {"error": "no data", "year": year, "sectors": []}
            continue

        fallback = "" if name else " [office-level]"
        print(f"{name or '(office-level)'}{fallback} — {len(sectors)} sectors, ${total:,.0f} total")

        output[dist] = {
            "candidate_name": name,
            "year": year,
            "total": int(total),
            "sectors": sectors,
        }

    return output


def main():
    senate_only   = "--senate-only"   in sys.argv
    assembly_only = "--assembly-only" in sys.argv

    result = {}

    if not assembly_only:
        result["state_senate"] = fetch_chamber(STATE_SENATE_OFFICES, "SD")

    if not senate_only:
        # Assembly offices TBD — run senate first to verify, then add assembly
        print("\n[Assembly not yet implemented — run with --senate-only for now]")
        result["assembly"] = {}

    out_path = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "..", "data", "ca-donor-sectors.json")
    )
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2)

    print(f"\nWritten to {out_path}")

    # Summary
    for chamber, data in result.items():
        if not data:
            continue
        covered = sum(1 for v in data.values() if v.get("sectors"))
        print(f"  {chamber}: {covered}/{len(data)} districts have sector data")


if __name__ == "__main__":
    main()
