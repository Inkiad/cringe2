#!/usr/bin/env python3
"""
fetch_votes.py

Fetches CA House rep votes on key bills from Congress.gov API.
Outputs: data/ca-votes.json

Usage:
    python scripts/fetch_votes.py

Requirements:
    pip install requests
"""

import requests
import json
import time
import os

# Set via env var or replace directly (do not commit to public repo)
API_KEY = os.environ.get("CONGRESS_API_KEY", "shJbAeGwaRBzpM7ZuS5vEpS1iG8mFB1HpcOGi5Iy")
BASE_URL = "https://api.congress.gov/v3"

# ── Bill list ─────────────────────────────────────────────────────────────────
# 2 bills per category. progressive_vote = which side is the progressive vote.
# None = too complex to assign a simple direction (weighting TBD).

BILLS = {
    "abortion": [
        {
            "congress": 118, "session": 1, "roll": 29,
            "label": "HR 26 — Born-Alive Abortion Survivors Protection Act",
            "progressive_vote": "Nay",
        },
        {
            "congress": 118, "session": 1, "roll": 30,
            "label": "HR 7 — No Taxpayer Funding for Abortion Act",
            "progressive_vote": "Nay",
        },
    ],
    "healthcare": [
        {
            "congress": 118, "session": 2, "roll": 40,
            "label": "HR 485 — Access to Family Building Act (IVF protection)",
            "progressive_vote": "Yea",
        },
        {
            "congress": 118, "session": 1, "roll": 708,
            "label": "HR 5378 — Lower Costs, More Transparency Act",
            "progressive_vote": "Yea",
        },
    ],
    "spending": [
        {
            "congress": 118, "session": 1, "roll": 216,
            "label": "HR 3746 — Fiscal Responsibility Act (Debt Ceiling)",
            "progressive_vote": None,  # bipartisan, complex
        },
        {
            "congress": 118, "session": 1, "roll": 380,
            "label": "HR 4366 — FY2024 Appropriations (House Republican spending bill)",
            "progressive_vote": "Nay",  # Dem opposition = opposed deep spending cuts
        },
    ],
    "immigration": [
        {
            "congress": 118, "session": 1, "roll": 209,
            "label": "HR 2 — Secure the Border Act",
            "progressive_vote": "Nay",
        },
        {
            "congress": 119, "session": 1, "roll": 23,
            "label": "S.5 — Laken Riley Act",
            "progressive_vote": "Nay",
        },
    ],
    "housing": [
        {
            "congress": 119, "session": 2, "roll": 57,
            "label": "HR 6644 — Housing for the 21st Century Act",
            "progressive_vote": "Yea",
        },
        {
            "congress": 119, "session": 2, "roll": 78,
            "label": "HR 4758 — Homeowner Energy Freedom Act",
            "progressive_vote": "Nay",
        },
    ],
}

# ── API helpers ───────────────────────────────────────────────────────────────

def api_get(path, params=None):
    url = f"{BASE_URL}{path}"
    p = {"api_key": API_KEY, "limit": 250, **(params or {})}
    resp = requests.get(url, params=p, timeout=60)
    resp.raise_for_status()
    time.sleep(0.4)  # stay well within rate limits
    return resp.json()


def api_get_all(path, list_key, params=None):
    """Paginate through all results for an endpoint."""
    results = []
    offset = 0
    while True:
        p = {**(params or {}), "offset": offset}
        data = api_get(path, p)
        page = data.get(list_key, [])
        results.extend(page)
        total = data.get("pagination", {}).get("count", 0)
        offset += len(page)
        if offset >= total or not page:
            break
    return results


def get_ca_house_members():
    """
    Returns {bioguideId: {"name": str, "district": str}} for current CA House reps.
    Paginates all 119th Congress members and filters to CA House members (have a district).
    """
    print("Fetching CA House members (paginating all 119th Congress members)...")
    all_members = api_get_all("/member/congress/119", "members")

    members = {}
    for m in all_members:
        if m.get("state") == "California" and m.get("district") is not None:
            house_terms = [
                t for t in m.get("terms", {}).get("item", [])
                if t.get("chamber") == "House of Representatives"
            ]
            since = min((t.get("startYear", 9999) for t in house_terms), default=None)
            members[m["bioguideId"]] = {
                "name": m["name"],
                "district": str(m["district"]),
                "since": since,
            }

    print(f"  Found {len(members)} CA House members")
    return members


def get_roll_call_votes(congress, session, roll):
    """
    Returns {bioguideId: vote_string} for every member on a given roll call.
    Response: houseRollCallVoteMemberVotes.results — not paginated, single dict.
    bioguide key: bioguideID (capital D), vote key: voteCast
    """
    path = f"/house-vote/{congress}/{session}/{roll}/members"
    print(f"  Roll call {congress}/{session}/{roll} ...", end=" ", flush=True)

    try:
        data = api_get(path, {"limit": 500})
    except requests.exceptions.HTTPError as e:
        print(f"ERROR {e.response.status_code} — skipping")
        return {}

    member_list = data.get("houseRollCallVoteMemberVotes", {}).get("results", [])

    # Normalize vote strings (API uses "Aye"/"No" on some votes, "Yea"/"Nay" on others)
    NORMALIZE = {"Aye": "Yea", "No": "Nay"}

    result = {}
    for m in member_list:
        bio = m.get("bioguideID")
        vote = NORMALIZE.get(m.get("voteCast", "Not Voting"), m.get("voteCast", "Not Voting"))
        if bio:
            result[bio] = vote

    print(f"{len(result)} member votes loaded")
    return result


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    ca_members = get_ca_house_members()

    # Initialise output structure
    output = {}
    for bio_id, info in ca_members.items():
        dist = info["district"]
        output[dist] = {
            "name": info["name"],
            "bioguideId": bio_id,
            "since": info.get("since"),
            "votes": {cat: [] for cat in BILLS},
        }

    # Fetch votes for each bill
    for category, bills in BILLS.items():
        print(f"\n[{category}]")
        for bill in bills:
            if bill["roll"] is None:
                print(f"  Skipping '{bill['label']}' — roll call number TBD")
                continue

            vote_map = get_roll_call_votes(bill["congress"], bill["session"], bill["roll"])

            for bio_id, info in ca_members.items():
                dist = info["district"]
                vote = vote_map.get(bio_id, "Not Found")
                output[dist]["votes"][category].append({
                    "label": bill["label"],
                    "congress": bill["congress"],
                    "session": bill["session"],
                    "roll": bill["roll"],
                    "vote": vote,
                    "progressive_vote": bill["progressive_vote"],
                })

    # Write output
    out_path = os.path.join(os.path.dirname(__file__), "..", "data", "ca-votes.json")
    out_path = os.path.normpath(out_path)
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\nDone. Written to {out_path}")
    print(f"Districts found: {sorted(output.keys(), key=lambda x: int(x))}")


if __name__ == "__main__":
    main()
