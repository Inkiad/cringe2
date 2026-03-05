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


def get_fec_candidate_id(district, expected_name=None):
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
        results = data.get("results", [])
        if not results:
            return None, None
        incumbents = results[:1]
    # When multiple incumbents (redistricting artifact), prefer the name match
    if len(incumbents) > 1 and expected_name:
        key = expected_name.split(",")[0].upper()
        match = next((c for c in incumbents if key in c.get("name", "").upper()), None)
        if match:
            return match.get("candidate_id"), match.get("name")
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


ACCEPTED_TYPES = {"PAC", "COM", "ORG"}
PAC_SKIP       = {"ACTBLUE", "WINRED", "ACTBLUE VENDOR SERVICES", "WINRED PAC"}


def get_committee_total_raised(committee_id):
    """Return total receipts for the committee in the current cycle."""
    try:
        data = fec_get(f"/committee/{committee_id}/totals/", {"cycle": CYCLE})
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return None
        raise
    results = data.get("results", [])
    if not results:
        return None
    return int(results[0].get("receipts", 0) or 0)


def get_pac_data(committee_id, n=5, max_pages=5):
    """
    Returns (top_donors, pac_count) where:
      top_donors — list of {name, total} for top N non-platform PAC donors
      pac_count  — total unique PAC/org contributors found
    Paginates up to max_pages to get past earmarked conduit record spam.
    """
    totals = {}
    cursor = {}  # holds last_index + last_contribution_receipt_amount for pagination

    for page in range(max_pages):
        params = {
            "committee_id": committee_id,
            "two_year_transaction_period": CYCLE,
            "entity_type": ["PAC", "COM", "ORG"],  # filter server-side; skip individual contributions
            "per_page": 100,
            "sort": "-contribution_receipt_amount",
            **cursor,
        }

        data = fec_get("/schedules/schedule_a/", params)
        results = data.get("results", [])
        if not results:
            break

        for item in results:
            if item.get("entity_type", "") not in ACCEPTED_TYPES:
                continue
            if item.get("memo_code") == "X":  # earmarked conduit — not a direct PAC contribution
                continue
            name = item.get("contributor_name", "").strip()
            amt  = item.get("contribution_receipt_amount", 0) or 0
            if name and amt > 0 and not looks_like_individual(name):
                totals[name] = totals.get(name, 0) + amt

        # Stop early if we have enough unique donors
        if len([k for k in totals if k.upper() not in PAC_SKIP]) >= n:
            break

        last_indexes = data.get("pagination", {}).get("last_indexes", {})
        if not last_indexes.get("last_index") or len(results) < 100:
            break
        cursor = {
            "last_index": last_indexes["last_index"],
            "last_contribution_receipt_amount": last_indexes.get("last_contribution_receipt_amount"),
        }

    pac_count   = len(totals)
    top_donors  = [
        {"name": name, "total": int(total)}
        for name, total in sorted(totals.items(), key=lambda x: -x[1])
        if name.upper() not in PAC_SKIP
    ][:n]

    return top_donors, pac_count


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
        candidate_id, fec_name = get_fec_candidate_id(dist, expected_name=rep_name)
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

        # Step 3: Top PAC donors + totals
        donors, pac_count = get_pac_data(committee_id)
        total_raised = get_committee_total_raised(committee_id)

        raised_str = f"${total_raised:,}" if total_raised is not None else "n/a"
        print(f"{len(donors)} donors, {pac_count} PACs, {raised_str} raised (top: {donors[0]['name'][:40] if donors else 'none'})")
        output[dist] = {
            "fec_id":        candidate_id,
            "committee_id":  committee_id,
            "cycle":         CYCLE,
            "total_raised":  total_raised,
            "pac_count":     pac_count,
            "donors":        donors,
        }

        # Save after each district so crashes don't lose progress
        with open(out_path, "w") as f:
            json.dump(output, f, indent=2)

    covered = sum(1 for v in output.values() if v.get("donors"))
    print(f"\nDone. {covered}/{len(districts)} districts have donor data.")
    print(f"Written to {out_path}")


if __name__ == "__main__":
    main()
