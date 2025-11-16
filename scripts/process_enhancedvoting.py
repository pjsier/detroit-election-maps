import csv
import json
import sys

if __name__ == "__main__":
    data = json.load(sys.stdin)

    precincts = data["ballotItemWithBreakdown"]["breakdownResults"]
    precinct_rows = []
    for precinct in precincts:
        precinct_row = {}
        precinct_name = precinct["precinct"]["name"][0]["text"]
        if "Precinct" not in precinct_name:
            continue

        precinct_row["id"] = precinct_name.split(" ")[-1]
        for ballot_option in precinct["ballotOptions"]:
            precinct_row[ballot_option["name"][0]["text"]] = ballot_option["voteCount"]
        precinct_rows.append(precinct_row)

    writer = csv.DictWriter(sys.stdout, fieldnames=list(precinct_rows[0].keys()))
    writer.writeheader()
    writer.writerows(precinct_rows)
