#!/usr/bin/env python3
"""
fetch_pac_donors.py

Fetches top 5 PAC donors for each CA House member from the FEC API.
Outputs: data/ca-pac-donors.json

Usage:
    python scripts/fetch_pac_donors.py

Requirements:
    pip install requests
"""

import requests
import json
import time
import os

FEC_KEY  = os.environ.get("FEC_API_KEY", "shJbAeGwaRBzpM7ZuS5vEpS1iG8mFB1HpcOGi5Iy")
FEC_BASE = "https://api.open.fec.gov/v1"

CYCLE = 2024  # most recent election cycle


def fec_get(path, params=None, retries=3):
    p = {"api_key": FEC_KEY, **(params or {})}
    for attempt in range(retries):
        try:
            resp = requests.get(f"{FEC_BASE}{path}", params=p, timeout=90)
            resp.raise_for_status()
            time.sleep(1.1)  # FEC allows 60 req/min; stay safely under
            return resp.json()
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            wait = 5 * (attempt + 1)
            print(f"(timeout, retrying in {wait}s)", end=" ", flush=True)
            time.sleep(wait)
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                print("(rate limited, waiting 65s)", end=" ", flush=True)
                time.sleep(65)
            else:
                raise
    raise RuntimeError(f"FEC API failed after {retries} retries: {path}")


def get_fec_candidate_id(district):
    """Find the incumbent's FEC candidate ID for a CA House district."""
    data = fec_get("/candidates/", {
        "state": "CA", "office": "H", "district": str(district).zfill(2),
        "election_year": CYCLE, "per_page": 10,
    })
    incumbents = [
        r for r in data.get("results", [])
        if r.get("incumbent_challenge_full") == "Incumbent"
    ]
    if not incumbents:
        # Fall back to highest-ID candidate if no incumbent flagged
        results = data.get("results", [])
        if not results:
            return None, None
        incumbents = results[:1]
    c = incumbents[0]
    return c.get("candidate_id"), c.get("name")


def get_principal_committee(candidate_id):
    """Return the principal campaign committee ID for a candidate."""
    data = fec_get(f"/candidate/{candidate_id}/committees/", {"designation": "P"})
    results = data.get("results", [])
    if not results:
        return None
    return results[0].get("committee_id")


def looks_like_individual(name):
    """Heuristic: FEC individual names are stored as LAST, FIRST — catch stragglers."""
    import re
    # Names like "SMITH, JOHN" or "DOE, JANE M." are individuals
    return bool(re.match(r'^[A-Z][A-Z\s\-\']+,\s+[A-Z]', name)) and "PAC" not in name and "COMMITTEE" not in name and "FUND" not in name and "ASSOCIATION" not in name and "UNION" not in name


def get_top_pac_donors(committee_id, n=5):
    """
    Return top N PAC donors to a committee in the current cycle.
    Fetches first 100 PAC receipts sorted by amount descending, aggregates
    by contributor name, and returns the top N. This is accurate because
    PAC hard-money contributions are capped at $10k/cycle, so the largest
    donors will always appear in the first page.
    """
    data = fec_get("/schedules/schedule_a/", {
        "committee_id": committee_id,
        "two_year_transaction_period": CYCLE,
        "per_page": 100,
        "sort": "-contribution_receipt_amount",
    })

    # Entity types to accept: PAC, COM (committee — most PACs/unions), ORG (tribal nations etc)
    # Exclude: IND (individual), PTY (party transfers), CCM (candidate-to-candidate transfers)
    ACCEPTED_TYPES = {"PAC", "COM", "ORG"}

    totals = {}
    for item in data.get("results", []):
        etype = item.get("entity_type", "")
        if etype not in ACCEPTED_TYPES:
            continue
        name = item.get("contributor_name", "").strip()
        amt  = item.get("contribution_receipt_amount", 0) or 0
        if name and amt > 0 and not looks_like_individual(name):
            totals[name] = totals.get(name, 0) + amt

    return [
        {"name": name, "total": int(total)}
        for name, total in sorted(totals.items(), key=lambda x: -x[1])[:n]
    ]


def main():
    votes_path = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "..", "data", "ca-votes.json")
    )
    with open(votes_path) as f:
        votes_data = json.load(f)

    out_path = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "..", "data", "ca-pac-donors.json")
    )

    # Load existing output so we can resume after a crash
    if os.path.exists(out_path):
        with open(out_path) as f:
            output = json.load(f)
        already_done = {k for k, v in output.items() if v.get("donors") is not None}
        print(f"Resuming — {len(already_done)} districts already complete.")
    else:
        output = {}
        already_done = set()

    districts = sorted(votes_data.keys(), key=int)
    print(f"Fetching top PAC donors for {len(districts)} CA House districts...\n")

    for dist in districts:
        if dist in already_done:
            print(f"  District {dist:>2} — skipped (already done)")
            continue

        rep_name = votes_data[dist].get("name", "?")
        print(f"  District {dist:>2} — {rep_name} ...", end=" ", flush=True)

        # Step 1: FEC candidate ID
        candidate_id, fec_name = get_fec_candidate_id(dist)
        if not candidate_id:
            print("no FEC candidate found")
            output[dist] = {"error": "no FEC candidate", "donors": []}
            continue

        # Step 2: Principal committee
        committee_id = get_principal_committee(candidate_id)
        if not committee_id:
            print(f"no committee for {candidate_id}")
            output[dist] = {"error": "no committee", "fec_id": candidate_id, "donors": []}
            continue

        # Step 3: Top PAC donors
        donors = get_top_pac_donors(committee_id)

        print(f"{len(donors)} donors (top: {donors[0]['name'][:40] if donors else 'none'})")
        output[dist] = {
            "fec_id":       candidate_id,
            "committee_id": committee_id,
            "cycle":        CYCLE,
            "donors":       donors,
        }

        # Save after each district so crashes don't lose progress
        with open(out_path, "w") as f:
            json.dump(output, f, indent=2)

    covered = sum(1 for v in output.values() if v.get("donors"))
    print(f"\nDone. {covered}/{len(districts)} districts have donor data.")
    print(f"Written to {out_path}")


if __name__ == "__main__":
    main()
