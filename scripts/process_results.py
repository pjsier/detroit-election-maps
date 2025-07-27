import json
import os
import pathlib
import sys

import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


if __name__ == "__main__":
    file_path = sys.argv[1]
    file_dir = os.path.basename(os.path.dirname(file_path))
    file_name = os.path.basename(file_path)

    election_dict = pd.read_excel(file_path, sheet_name=None)

    output_map = {"0": "TURNOUT"}

    for race in election_dict.keys():
        output_dir = os.path.join(
            BASE_DIR, "data", "output", file_dir, file_name.split(".")[0]
        )
        pathlib.Path(output_dir).mkdir(parents=True, exist_ok=True)

        # Get int at the end of the race and make it the key
        race_key = race.split(" ")[-1]
        election_df = pd.read_excel(
            os.path.join(sys.argv[1]),
            sheet_name=race,
            skiprows=6,
        ).rename(columns={"Precinct": "id"})
        # Load the clean race title from the ID
        election_df["id"] = election_df["id"].apply(lambda p: p.split(" ")[-1])
        election_df = election_df[election_df.columns[1:]]
        election_df.to_csv(
            os.path.join(output_dir, f"{race_key}.csv"),
            index=False,
        )
        output_map[race_key] = " ".join(race.split(" ")[:-1])

    with open(
        os.path.join(
            BASE_DIR,
            "data",
            "output",
            file_dir,
            file_name.split(".")[0],
            "metadata.json",
        ),
        "w",
    ) as f:
        json.dump(output_map, f)
