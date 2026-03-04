#!/usr/bin/env python3
"""
fetch_state_votes.py

Fetches CA state senate and assembly votes on key bills from LegiScan API.
Outputs: data/ca-state-votes.json

Usage:
    python scripts/fetch_state_votes.py

Requirements:
    pip install requests
"""

import requests
import json
import time
import os
import re

API_KEY = os.environ.get("LEGISCAN_API_KEY", "e4c7899f760c5abce0a554a8c6ab58d3")
BASE_URL = "https://api.legiscan.com/"

# Bills: each entry has senate_rc and/or assembly_rc roll call IDs from LegiScan.
# "featured": True = shown by default in the UI (top 2 per category, biased toward newer).
# All bills are stored in the JSON; the UI filters on featured.
#
# Note: the immigration 2nd entry (SB 245/AB 311) uses companion bills —
# SB 245 had the Senate vote, AB 311 had the Assembly vote (same policy).
BILLS = {
    "housing": [
        {
            "label": "SB 79 — Transit-Oriented Housing Development (2025)",
            "senate_rc": 1584417,    # 21-13
            "assembly_rc": 1602370,  # 43-19
            "progressive_vote": "Yea",
            "featured": True,
        },
        {
            "label": "SB 423 — Streamlined Multi-Family Housing Approval (2023)",
            "senate_rc": 1336335,    # 29-5
            "assembly_rc": 1353456,  # 61-8
            "progressive_vote": "Yea",
            "featured": True,
        },
        {
            "label": "AB 1033 — ADU Ownership and Separate Sale (2023)",
            "senate_rc": 1353191,    # 21-14
            "assembly_rc": 1338185,  # 50-16
            "progressive_vote": "Yea",
            "featured": False,
        },
    ],
    "healthcare": [
        {
            "label": "SB 525 — Healthcare Worker Minimum Wage (2023)",
            "senate_rc": 1336368,    # 21-11
            "assembly_rc": 1354816,  # 63-13
            "progressive_vote": "Yea",
            "featured": True,
        },
        {
            "label": "AB 45 — Health Data Location Privacy (2025)",
            "senate_rc": 1602297,    # 29-9
            "assembly_rc": 1602298,  # 61-12
            "progressive_vote": "Yea",
            "featured": True,
        },
        {
            "label": "SB 582 — Health Data Privacy Protections (2023)",
            "senate_rc": 1332651,    # 39-0 (unanimous in Senate)
            "assembly_rc": 1353513,  # 61-16
            "progressive_vote": "Yea",
            "featured": False,
        },
    ],
    "abortion": [
        {
            "label": "AB 82 — Healthcare Shield Law (2025)",
            "senate_rc": 1601680,    # 29-8
            "assembly_rc": 1602442,  # 61-12
            "progressive_vote": "Yea",
            "featured": True,
        },
        {
            "label": "AB 352 — Abortion Provider Shield Law (2023)",
            "senate_rc": 1354379,    # 32-7
            "assembly_rc": 1338102,  # 64-12
            "progressive_vote": "Yea",
            "featured": True,
        },
        {
            "label": "AB 260 — Reproductive Health Care Act (2025)",
            "senate_rc": 1601536,    # 30-8
            "assembly_rc": 1602425,  # 61-12
            "progressive_vote": "Yea",
            "featured": False,
        },
        {
            "label": "SB 541 — Reproductive Health Services Access (2023)",
            "senate_rc": 1336385,    # 31-9
            "assembly_rc": 1353444,  # 65-11
            "progressive_vote": "Yea",
            "featured": False,
        },
    ],
    "lgbtq": [
        {
            "label": "AB 1955 — SAFETY Act: Student Gender Identity Protection (2024)",
            "senate_rc": 1457334,    # 29-8
            "assembly_rc": 1461238,  # 61-16
            "progressive_vote": "Yea",
            "featured": True,
        },
        {
            "label": "SB 407 — LGBTQ+ Foster Care Family Protections (2023)",
            "senate_rc": 1332608,    # 31-5
            "assembly_rc": 1354098,  # 61-14
            "progressive_vote": "Yea",
            "featured": True,
        },
    ],
    "immigration": [
        {
            "label": "SB 98 — Limit ICE Enforcement at Schools and Universities (2025)",
            "senate_rc": 1586398,    # 29-8
            "assembly_rc": 1600846,  # 59-10
            "progressive_vote": "Yea",
            "featured": True,
        },
        {
            "label": "AB 1306 — Limit Local Immigration Enforcement Cooperation (2023)",
            "senate_rc": 1354836,    # 29-9
            "assembly_rc": 1335465,  # 54-18
            "progressive_vote": "Yea",
            "featured": True,
        },
        {
            # Companion bills on same policy: SB 245 had Senate vote, AB 311 had Assembly vote
            "label": "SB 245/AB 311 — Food Assistance Regardless of Immigration Status (2023)",
            "senate_rc": 1332612,    # SB 245 Senate floor vote (31-8)
            "assembly_rc": 1338192,  # AB 311 Assembly floor vote (64-15)
            "progressive_vote": "Yea",
            "featured": False,
        },
    ],
    "spending": [
        {
            "label": "AB 1228 — Fast Food Minimum Wage ($20/hour) (2023)",
            "senate_rc": 1354781,    # 32-8
            "assembly_rc": 1338010,  # 42-22
            "progressive_vote": "Yea",
            "featured": True,
        },
        {
            "label": "SB 140 — Early Childcare and Education Funding (2023)",
            "senate_rc": 1285749,    # 29-8
            "assembly_rc": 1353573,  # 61-10
            "progressive_vote": "Yea",
            "featured": True,
        },
    ],
}

_people_cache = {}


def legiscan_get(op, params=None):
    p = {"op": op, "key": API_KEY, **(params or {})}
    resp = requests.get(BASE_URL, params=p, timeout=60)
    resp.raise_for_status()
    time.sleep(0.5)  # stay within rate limits
    return resp.json()


def get_roll_call_votes(roll_call_id):
    """Returns {people_id: vote_text} for every member on a given roll call."""
    print(f"  rc {roll_call_id} ...", end=" ", flush=True)
    try:
        data = legiscan_get("getRollCall", {"id": roll_call_id})
    except requests.exceptions.HTTPError as e:
        print(f"ERROR {e.response.status_code} — skipping")
        return {}
    rc = data.get("roll_call", {})
    votes = rc.get("votes", [])
    result = {v["people_id"]: v.get("vote_text", "Not Voting") for v in votes if "people_id" in v}
    print(f"{len(result)} votes")
    return result


def get_person(people_id):
    """Returns {role, district} for a LegiScan people_id, cached."""
    if people_id in _people_cache:
        return _people_cache[people_id]
    try:
        data = legiscan_get("getPerson", {"id": people_id})
    except Exception:
        _people_cache[people_id] = None
        return None
    p = data.get("person", {})
    district_raw = str(p.get("district", ""))
    # Strip state prefix and leading zeros: "CA-012" -> "12", "012" -> "12"
    district = re.sub(r"^[A-Za-z]+-?", "", district_raw).lstrip("0") or "0"
    info = {
        "role": p.get("role", ""),  # "Rep" = Assembly, "Sen" = State Senate
        "district": district,
        "name": p.get("name", ""),
    }
    _people_cache[people_id] = info
    return info


def chamber_key(role):
    if role == "Sen":
        return "state_senate"
    if role == "Rep":
        return "assembly"
    return None


def main():
    reps_path = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "..", "data", "ca-reps.json")
    )
    with open(reps_path) as f:
        reps = json.load(f)

    # Initialize output: district -> {name, votes: {category: []}}
    output = {
        "state_senate": {
            dist: {"name": rep["name"], "votes": {cat: [] for cat in BILLS}}
            for dist, rep in reps["state_senate"].items()
        },
        "assembly": {
            dist: {"name": rep["name"], "votes": {cat: [] for cat in BILLS}}
            for dist, rep in reps["assembly"].items()
        },
    }

    # Build list of (category, label, progressive_vote, featured, chamber_key, rc_id)
    tasks = []
    for cat, bills in BILLS.items():
        for bill in bills:
            featured = bill.get("featured", False)
            if bill.get("senate_rc"):
                tasks.append((cat, bill["label"], bill["progressive_vote"], featured, "state_senate", bill["senate_rc"]))
            if bill.get("assembly_rc"):
                tasks.append((cat, bill["label"], bill["progressive_vote"], featured, "assembly", bill["assembly_rc"]))

    # Step 1: fetch all roll calls
    print(f"Fetching {len(tasks)} roll calls...\n")
    rc_data = {}
    all_people_ids = set()
    prev_cat = None
    for cat, label, prog, featured, chkey, rc_id in tasks:
        if cat != prev_cat:
            print(f"[{cat}]")
            prev_cat = cat
        votes = get_roll_call_votes(rc_id)
        rc_data[rc_id] = votes
        all_people_ids.update(votes.keys())

    # Step 2: resolve all people_ids -> (role, district) via getPerson
    print(f"\nResolving {len(all_people_ids)} unique legislators via getPerson...")
    for i, pid in enumerate(sorted(all_people_ids), 1):
        get_person(pid)
        if i % 20 == 0:
            print(f"  {i}/{len(all_people_ids)}...")
    print(f"  Done ({len(all_people_ids)} legislators resolved)\n")

    # Step 3: apply votes to output
    for cat, label, prog, featured, chkey, rc_id in tasks:
        vote_map = rc_data[rc_id]
        unmatched = []
        for pid, vote_text in vote_map.items():
            info = _people_cache.get(pid)
            if not info:
                continue
            actual_chamber = chamber_key(info["role"])
            if actual_chamber != chkey:
                continue  # skip legislators from the wrong chamber
            dist = info["district"]
            if dist in output[chkey]:
                output[chkey][dist]["votes"][cat].append({
                    "label": label,
                    "vote": vote_text,
                    "progressive_vote": prog,
                    "featured": featured,
                })
            else:
                unmatched.append((info.get("name", pid), dist))
        if unmatched:
            print(f"  [{cat}] unmatched in {chkey}: {unmatched[:5]}")

    # Write output
    out_path = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "..", "data", "ca-state-votes.json")
    )
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"Written to {out_path}")

    # Coverage summary
    for chkey in ("state_senate", "assembly"):
        total = len(output[chkey])
        covered = sum(
            1 for v in output[chkey].values()
            if any(len(v["votes"][cat]) > 0 for cat in BILLS)
        )
        print(f"  {chkey}: {covered}/{total} districts have votes")


if __name__ == "__main__":
    main()
