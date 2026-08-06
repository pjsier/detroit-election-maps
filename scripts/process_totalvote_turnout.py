import json
import csv
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    year = [val for val in output_file.split("/") if val.isdigit()][0]

    with open(
        os.path.join(BASE_DIR, "data", "precincts", f"map-{year}.json"), "r"
    ) as f:
        id_map = json.load(f)

    with open(input_file, "r") as f:
        turnout = json.load(f)

    with open(output_file, "w") as f:
        writer = csv.DictWriter(
            f, fieldnames=["id", "name", "ballots", "registered", "turnout"]
        )
        writer.writeheader()
        for turnout_row in turnout:
            turnout_val = 0
            if turnout_row["Voters"] > 0:
                turnout_val = round(
                    (turnout_row["calcVoterTurnout"] / turnout_row["Voters"]) * 100, 2
                )
            writer.writerow(
                {
                    "id": id_map[turnout_row["PrecinctName"]],
                    "name": turnout_row["PrecinctName"],
                    "ballots": turnout_row["calcVoterTurnout"],
                    "registered": turnout_row["Voters"],
                    "turnout": turnout_val,
                }
            )
