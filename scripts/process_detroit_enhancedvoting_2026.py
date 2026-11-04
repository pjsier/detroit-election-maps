import requests
import json
from collections import defaultdict
from pathlib import Path
import sys
import re
import csv
import os

BASE_URL = "https://app.enhancedvoting.com/results/public/api/elections/city-detroit-mi/_20261027152933"

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

YEAR = "2026"

TOTAL = "Total"
ELECTION_DAY = "Election Day"
ALL_EARLY = "All Early Votes"
OUTPUT_VOTE_TYPES = (TOTAL, ELECTION_DAY, ALL_EARLY)
CB_PATTERN = re.compile(r"\bCB\s*(\d+)\s*$", re.IGNORECASE)
NON_VALUE_COLS = {"id", "name", "board", "over_votes", "under_votes"}


def slugify(text):
    return (
        re.sub(
            r"\s",
            "-",
            re.sub(r"\s+", " ", re.sub(r"[^a-z\d]", " ", text.lower())).strip(),
        )
        .replace("-for-", "-")
        .replace("-state-senate", "")
    )


def normalize_precinct(value):
    value = str(value).strip()
    return str(int(value)) if value.isdigit() else value


def counting_board_id(name):
    match = CB_PATTERN.search(name)
    return normalize_precinct(match.group(1)) if match else None


def precinct_token(name):
    match = re.search(r"(\d+)\s*$", name)
    return normalize_precinct(match.group(1) if match else name.split()[-1])


def load_precinct_board_map(year):
    with open(os.path.join(BASE_DIR, "data", "counting-boards", f"{year}.csv"), "r") as f:
        return {
            normalize_precinct(r["precinct"]): normalize_precinct(r["board"])
            for r in csv.DictReader(f)
        }


def lookup_id(name, id_map):
    """Counting board rows have no precinct id; every other row must be in the map."""
    if counting_board_id(name) is not None:
        return id_map.get(name, "")
    return id_map[name]


def to_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def build_board_rows(rows, turnout_by_name, precinct_board_map, label):
    has_over_under = "over_votes" in rows[0]
    has_ballots = "ballots" in rows[0]
    # Ballots are None when the API doesn't give them (e.g. per vote type)
    ballots_known = has_ballots and rows[0]["ballots"] is not None

    # Attach registered, work out each row's board and aggregation key
    prepared = []
    value_cols = []
    for row in rows:
        row = dict(row)
        row["registered"] = turnout_by_name.get(row["name"], {}).get("registered", 0)

        cb_id = counting_board_id(row["name"])
        row["is_cb_row"] = cb_id is not None
        row["board"] = (
            cb_id
            if cb_id is not None
            else precinct_board_map.get(precinct_token(row["name"]), "")
        )
        if not row["is_cb_row"] and not row["board"]:
            print(f"{label}: no counting board for {row['name']}")

        # Shared key per board; unmatched precincts stay on their own
        row["key"] = f"board:{row['board']}" if row["board"] else f"name:{row['name']}"
        prepared.append(row)

        for col in row:
            if col not in NON_VALUE_COLS | {"is_cb_row", "key"} and col not in value_cols:
                value_cols.append(col)

    # Sum every value column per board
    totals = defaultdict(lambda: defaultdict(int))
    for row in prepared:
        for col in value_cols:
            totals[row["key"]][col] += to_int(row.get(col))

    candidate_cols = [c for c in value_cols if c not in ("ballots", "registered")]

    entries = [r for r in prepared if not r["is_cb_row"]]

    out = []
    for row in entries:
        agg = totals[row["key"]]
        out_row = {"id": row["id"], "name": row["name"], "board": row["board"]}
        if has_ballots:
            out_row["ballots"] = agg["ballots"] if ballots_known else ""
        if has_over_under:
            out_row["over_votes"] = ""
            out_row["under_votes"] = ""
        for col in candidate_cols:
            out_row[col] = agg[col]
        out_row["registered"] = agg["registered"]
        if has_ballots:
            # Blank (like Wayne's NaN) when there's nothing to divide by
            out_row["turnout"] = (
                round(agg["ballots"] / agg["registered"] * 100, 2)
                if ballots_known and agg["registered"]
                else ""
            )
        out.append(out_row)
    return out


def process_ballot_item(item_id, id_map, turnout_by_name):
    """
    Returns {vote_type: [row, ...]} with one row per precinct (and counting board).
    Vote types: Total, Election Day and "All Early Votes" (Total minus Election Day).

    Row columns match the Wayne precinct files:
    name, ballots, over_votes, under_votes, <candidates>, total, id
    """
    res = requests.get(f"{BASE_URL}/data/ballot-item/{item_id}")
    data = res.json()

    results = defaultdict(list)

    for item in data["ballotItemWithBreakdown"]["breakdownResults"]:
        precinct_name = item["precinct"]["name"][0]["text"]
        precinct_id = lookup_id(precinct_name, id_map)

        candidates = [o["name"][0]["text"] for o in item["ballotOptions"]]
        votes = {TOTAL: {c: 0 for c in candidates}}
        for option in item["ballotOptions"]:
            candidate = option["name"][0]["text"]
            votes[TOTAL][candidate] = to_int(option["voteCount"])
            for group in option.get("groupResults") or []:
                vote_type = group["groupName"][0]["text"].strip()
                if vote_type.lower() == ELECTION_DAY.lower():
                    vote_type = ELECTION_DAY
                votes.setdefault(vote_type, {c: 0 for c in candidates})
                votes[vote_type][candidate] = to_int(group["voteCount"])

        if len(votes) == 1:
            print(f"warning: no groupResults for {precinct_name}, only Total will be written")

        # All early votes is simply everything that isn't Election Day
        if len(votes) > 1:
            election_day = votes.get(ELECTION_DAY, {})
            votes[ALL_EARLY] = {
                c: votes[TOTAL][c] - election_day.get(c, 0) for c in candidates
            }

        for vote_type, candidate_votes in votes.items():
            if vote_type not in OUTPUT_VOTE_TYPES:
                continue
            # Ballots cast are only available overall, not per vote type
            ballots = (
                turnout_by_name.get(precinct_name, {}).get("ballots", 0)
                if vote_type == TOTAL
                else None
            )
            row = {
                "name": precinct_name,
                "ballots": ballots,
                "over_votes": "",
                "under_votes": "",
            }
            row.update(candidate_votes)
            row["total"] = sum(candidate_votes.values())
            row["id"] = precinct_id
            results[vote_type].append(row)

    return results


def write_csv(path, rows):
    # Union of keys (in first-seen order) in case some rows lack a candidate
    fieldnames = list(dict.fromkeys(key for row in rows for key in row))
    with Path.open(path, "w") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, restval=0)
        writer.writeheader()
        writer.writerows(rows)


def main():
    output_dir = Path(sys.argv[1])
    output_dir.mkdir(parents=True, exist_ok=True)

    precinct_board_map = load_precinct_board_map(YEAR)

    with open(os.path.join(BASE_DIR, "data", "precincts", f"map-{YEAR}.json"), "r") as f:
        id_map = {k: str(int(v)) for k, v in json.load(f).items()}

    res = requests.get(f"{BASE_URL}/data")
    data = res.json()

    turnout = []
    for precinct in data["voterTurnout"]:
        if precinct["voterRegistration"] == 0:
            turnout_val = 0.0
        else:
            turnout_val = round(
                (precinct["ballotsCast"] / precinct["voterRegistration"]) * 100, 2
            )
        turnout.append(
            {
                "id": lookup_id(precinct["precinctName"], id_map),
                "name": precinct["precinctName"],
                "ballots": precinct["ballotsCast"],
                "registered": precinct["voterRegistration"],
                "turnout": turnout_val,
            }
        )
    turnout_by_name = {t["name"]: t for t in turnout}

    # Precinct-level turnout excludes counting board rows
    write_csv(
        output_dir / "turnout.csv",
        [t for t in turnout if counting_board_id(t["name"]) is None],
    )

    # Counting-board turnout
    write_csv(
        output_dir / "turnout-cb.csv",
        build_board_rows(
            [{"id": t["id"], "name": t["name"], "ballots": t["ballots"]} for t in turnout],
            turnout_by_name,
            precinct_board_map,
            "turnout",
        ),
    )

    for ballot_item in data["ballotItems"]:
        item_name = ballot_item["name"][0]["text"]
        print(item_name)

        by_vote_type = process_ballot_item(ballot_item["id"], id_map, turnout_by_name)
        slug = slugify(item_name)

        for vote_type, rows in by_vote_type.items():
            suffix = "" if vote_type == TOTAL else f"-{slugify(vote_type)}"
            label = f"{slug}{suffix}"

            write_csv(
                output_dir / f"{label}.csv",
                [r for r in rows if counting_board_id(r["name"]) is None],
            )
            write_csv(
                output_dir / f"{label}-cb.csv",
                build_board_rows(rows, turnout_by_name, precinct_board_map, label),
            )


if __name__ == "__main__":
    main()
