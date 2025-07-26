import os
import sys

import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


if __name__ == "__main__":
    file_path = sys.argv[1]
    file_dir = os.path.basename(os.path.dirname(file_path))
    file_name = os.path.basename(file_path)

    turnout_df = pd.read_json(file_path).rename(
        columns={"calcVoterTurnout": "ballots", "Voters": "registered"}
    )
    turnout_df = turnout_df[turnout_df["registered"] > 0]
    turnout_df["id"] = turnout_df["PrecinctName"].apply(lambda p: p.split(" ")[-1])
    turnout_df = turnout_df[["id", "ballots", "registered"]]
    turnout_df["turnout"] = (
        (turnout_df["ballots"] / turnout_df["registered"]) * 100
    ).round(2)

    turnout_df.to_csv(
        os.path.join(
            BASE_DIR,
            "data",
            "output",
            file_dir,
            " ".join(file_name.split("-")[:-1]),
            "0.csv",
        ),
        index=False,
    )
