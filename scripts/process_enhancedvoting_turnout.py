import csv
import json
import sys

if __name__ == "__main__":
    data = json.load(sys.stdin)

    precincts = data["voterTurnout"]
    precinct_rows = []
    for precinct in precincts:
        precinct_name = precinct["precinctName"]
        if "Precinct" not in precinct_name:
            continue

        if precinct["voterRegistration"] == 0:
            turnout = 0.0
        else:
            turnout = round(
                (precinct["ballotsCast"] / precinct["voterRegistration"]) * 100.0, 2
            )
        precinct_rows.append(
            {
                "id": precinct_name.split(" ")[-1],
                "ballots": precinct["ballotsCast"],
                "registered": precinct["voterRegistration"],
                "turnout": turnout,
            }
        )

    writer = csv.DictWriter(
        sys.stdout, fieldnames=["id", "ballots", "registered", "turnout"]
    )
    writer.writeheader()
    writer.writerows(precinct_rows)
