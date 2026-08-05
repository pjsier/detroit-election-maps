import requests
import json
from pathlib import Path
import sys
import re
import csv
import os

BASE_URL = "https://app.enhancedvoting.com/results/public/api/elections/city-detroit-mi/Detroit-Primary-Election08042026"

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


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


def process_ballot_item(item_id, candidate_map, id_map):
    res = requests.get(f"{BASE_URL}/data/ballot-item/{item_id}")
    data = res.json()

    results = []

    for item in data["ballotItemWithBreakdown"]["breakdownResults"]:
        precinct_name = item["precinct"]["name"][0]["text"]
        result_obj = {
            "id": id_map[precinct_name],
            "name": precinct_name,
            "over_votes": "",
            "under_votes": "",
        }
        total = 0
        for ballot_option in item["ballotOptions"]:
            total += ballot_option["voteCount"]
            result_obj[ballot_option["name"][0]["text"]] = ballot_option["voteCount"]
        result_obj["total"] = total
        results.append(result_obj)

    return results


def main():
    output_dir = Path(sys.argv[1])

    with open(os.path.join(BASE_DIR, "data", "precincts", "map-2026.json"), "r") as f:
        id_map = json.load(f)

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
                "id": id_map[precinct["precinctName"]],
                "name": precinct["precinctName"],
                "ballots": precinct["ballotsCast"],
                "registered": precinct["voterRegistration"],
                "turnout": turnout_val,
            }
        )
    with Path.open(output_dir / "turnout.csv", "w") as f:
        writer = csv.DictWriter(f, fieldnames=list(turnout[0].keys()))
        writer.writeheader()
        writer.writerows(turnout)

    for ballot_item in data["ballotItems"]:
        item_name = ballot_item["name"][0]["text"]
        print(item_name)
        candidate_map = {}
        for ballot_option in ballot_item["summaryResults"]["ballotOptions"]:
            candidate_map[ballot_option["id"]] = ballot_option["name"][0]["text"]

        item_results = process_ballot_item(ballot_item["id"], candidate_map, id_map)
        with Path.open(output_dir / f"{slugify(item_name)}.csv", "w") as f:
            writer = csv.DictWriter(f, fieldnames=list(item_results[0].keys()))
            writer.writeheader()
            writer.writerows(item_results)


if __name__ == "__main__":
    main()
