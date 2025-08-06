import json
import os
import sys
from collections import defaultdict

import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


if __name__ == "__main__":
    file_path = sys.argv[1]
    file_dir = os.path.basename(os.path.dirname(file_path))
    file_name = os.path.basename(file_path)

    with open(file_path, "r") as f:
        data = json.load(f)

    precinct_output = defaultdict(dict)
    race_key = data[0]["RaceID"]
    for rec in data:
        if "Precinct" not in rec["PrecinctName"]:
            continue
        precinct_key = rec["PrecinctName"].split(" ")[-1]
        candidate = rec["calcCandidate"].strip()
        precinct_output[precinct_key][candidate] = rec["calcCandidateVotes"]

    output_records = []
    for key, item in precinct_output.items():
        output_records.append({"id": key, **item})
    output_df = pd.DataFrame(output_records)

    output_df.to_csv(
        os.path.join(
            BASE_DIR,
            "data",
            "output",
            file_dir,
            file_name.split("-")[0],
            f"{race_key}.csv",
        ),
        index=False,
    )
