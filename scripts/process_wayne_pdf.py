import csv
import os
import re
import sys
import json

import pandas as pd
import pdfplumber

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def clean_header(header):
    return re.sub(r"\s+", " ", header.replace("NP -", "").replace("DEM -", "").replace("REP -", "")).strip()


def slugify(text):
    return re.sub(
        r"\s", "-", re.sub(r"\s+", " ", re.sub(r"[^a-z\d]", " ", text.lower())).strip()
    )


def get_rotated_headers(page):
    words = page.extract_words(keep_blank_chars=True)
    vertical_words = [w for w in words if not w["upright"]]
    if not vertical_words:
        return [], 0, []
    header_bottom = max(w["bottom"] for w in vertical_words)
    sorted_words = sorted(vertical_words, key=lambda w: w["x0"])
    columns = [[sorted_words[0]]]
    for w in sorted_words[1:]:
        if w["x0"] - columns[-1][-1]["x1"] < 5:
            columns[-1].append(w)
        else:
            columns.append([w])
    headers = [
        " ".join(w["text"].strip() for w in sorted(col, key=lambda w: w["top"]))
        for col in columns
    ]
    col_centers = [
        (min(w["x0"] for w in g) + max(w["x1"] for w in g)) / 2 for g in columns
    ]
    # Split point: just left of the first rotated header strip
    data_split = min(w["x0"] for w in sorted_words) - 7
    return headers, header_bottom, col_centers, data_split


def assign_to_col(x, col_centers):
    return min(range(len(col_centers)), key=lambda i: abs(col_centers[i] - x))


def extract_race_title(page):
    text = page.extract_text()
    if not text:
        return None
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    if not lines:
        return None

    # First line is always the title; split off any second race
    # e.g. "1 Mayor - City of Detroit     2 Clerk - City of Detroit"
    race_title = re.split(r"\s{2,}(?=\d+\s)", lines[0])[0].strip()

    # If the second line continues the title (not a digit-only candidate
    # number row like "1 1 1 1" and not a new numbered item), append it
    if (
        len(lines) > 1
        and not re.match(r"^[\d\s]+$", lines[1])
        and not re.match(r"^\d+\s", lines[1])
    ):
        race_title += " " + lines[1]

    # TODO: remove numbers and extra detroit mentions
    race_title = re.sub(
        r"\s+",
        " ",
        (
            race_title.replace("City of Detroit", "")
            .replace("Detroit", "")
            .strip()
            .lstrip("1")
        ),
    )
    if "- 2" in re.sub(r"\s+", " ", race_title):
        race_title = race_title.split("- 2")[0]

    race_title_slug = slugify(race_title)
    # Sometimes the next line gets pulled in, so strip it out manually if it does
    if "-voters" in race_title_slug:
        race_title_slug = race_title_slug.split("-voters")[0]

    return race_title_slug.replace("-state-senate-", "")


def extract_page_table(page, label_cols=("Precinct", "Vote Type")):
    col_headers, header_bottom, col_centers, data_split = get_rotated_headers(page)
    if not col_headers:
        return None

    all_words = page.extract_words(keep_blank_chars=True)
    data_words = sorted(
        [
            w
            for w in all_words
            if w["upright"]
            and w["top"] > header_bottom
            and w["bottom"] < page.height - 30
        ],
        key=lambda w: w["top"],
    )

    # Group words into rows. Normal row gap ~11.8pts; "Pre-Process" continuation
    # line is ~7.9pts below — threshold of 9 splits them correctly.
    ROW_GAP = 9
    rows = []
    for w in data_words:
        if not rows or w["top"] - rows[-1][0]["top"] > ROW_GAP:
            rows.append([w])
        else:
            rows[-1].append(w)

    # Merge "Pre-Process\nAbsentee" continuation rows — they have only a
    # vote-type label word and no precinct or data words.
    merged_rows = []
    for row in rows:
        label_words = [w for w in row if (w["x0"] + w["x1"]) / 2 < data_split]
        data_word_list = [w for w in row if (w["x0"] + w["x1"]) / 2 >= data_split]
        precinct_words = [w for w in label_words if w["x0"] < 100]
        vote_type_words = [w for w in label_words if w["x0"] >= 100]
        is_continuation = not precinct_words and not data_word_list and vote_type_words
        if is_continuation and merged_rows:
            merged_rows[-1]["vote_type"] += " " + " ".join(
                w["text"].strip() for w in vote_type_words
            )
        else:
            merged_rows.append(
                {
                    "precinct": " ".join(w["text"].strip() for w in precinct_words),
                    "vote_type": " ".join(w["text"].strip() for w in vote_type_words),
                    "data": data_word_list,
                }
            )

    all_headers = list(label_cols) + col_headers
    records = []
    current_precinct = ""
    for row in merged_rows:
        if row["precinct"]:
            current_precinct = row["precinct"]
        row_data = [""] * len(col_headers)
        for w in row["data"]:
            col_idx = assign_to_col((w["x0"] + w["x1"]) / 2, col_centers)
            row_data[col_idx] = (row_data[col_idx] + " " + w["text"].strip()).strip()
        records.append([current_precinct, row["vote_type"]] + row_data)

    return pd.DataFrame(
        records, columns=[clean_header(header) for header in all_headers]
    )


def specific_race_overrides(df_map):
    if (
        ("mayor" in df_map)
        and ("Janice M. Winfrey" in df_map["mayor"].columns)
        and ("Janice M. Winfrey" not in df_map["clerk"].columns)
    ):
        winfrey_df = df_map["mayor"][["Precinct", "Vote Type", "Janice M. Winfrey"]]
        df_map["clerk"] = pd.merge(
            df_map["clerk"], winfrey_df, how="left", on=["Precinct", "Vote Type"]
        )
        df_map["mayor"] = df_map["mayor"].drop("Janice M. Winfrey", axis=1)
    return df_map


def assert_totals_match(race_name, df):
    df["Voters Cast"] = (
        pd.to_numeric(df["Voters Cast"], errors="coerce").fillna(0).astype(int)
    )
    total_votes = df.loc[df["Vote Type"] == "Total"]["Voters Cast"].sum()
    total_row_votes = df.loc[df["Precinct"] == "Contest Total"].iloc[0]["Voters Cast"]
    assert total_votes == total_row_votes
    print(f"{race_name} totals match")


if __name__ == "__main__":
    input_file = sys.argv[1]
    output_dir = sys.argv[2]
    year = [val for val in output_dir.split("/") if val.isdigit()][0]

    os.makedirs(output_dir, exist_ok=True)

    with open(os.path.join(BASE_DIR, "data", "precincts", f"map-{year}.json"), "r") as f:
        id_map = json.load(f)

    df_list: list[pd.DataFrame] = []
    df_map: dict[str, pd.DataFrame] = {}
    precinct_board_map = {}

    with pdfplumber.open(input_file) as pdf:
        for idx, page in enumerate(pdf.pages):
            title = extract_race_title(page)
            df = extract_page_table(page)
            if year == "2025":
                df = df.loc[df["Precinct"].str.contains("Detroit")]
            if title is None:
                print(idx, df.columns)

            if title in df_map:
                if df_map[title].columns.equals(df.columns):
                    df_map[title] = pd.concat(
                        [df_map[title], df], axis=0, ignore_index=True
                    )
                else:
                    # If the title is already in the map, but we see different columns,
                    # then we need to merge rather than concatenate
                    diff_cols = list(set(df) - set(df_map[title].columns))
                    df_to_merge = df[["Precinct", "Vote Type"] + diff_cols]
                    df_map[title] = pd.merge(
                        df_map[title],
                        df_to_merge,
                        on=["Precinct", "Vote Type"],
                        how="left",
                    )
            else:
                df_map[title] = df

    if year == "2025":
        df_map = specific_race_overrides(df_map)
        with open(
            os.path.join(BASE_DIR, "data", "counting-boards", f"{year}.csv"), "r"
        ) as f:
            reader = csv.DictReader(f)
            precinct_board_map = {r["precinct"]: r["board"] for r in reader}

    # Pull the first-added race into a subset for turnout
    df_map["turnout"] = df_map[list(df_map.keys())[0]][
        [
            "Precinct",
            "Vote Type",
            "Voters Cast",
            "Registered Voters",
            "Turnout (%)",
        ]
    ]

    for race_key, df_val in df_map.items():
        df_val = df_val.loc[:, ~df_val.columns.duplicated()]
        # TODO: Only run for Detroit-specific
        # assert_totals_match(race_key, df_val)
        for col in df_val.columns:
            if col in ["Precinct", "Vote Type", "Turnout (%)"]:
                continue
            df_val[col] = (
                pd.to_numeric(df_val[col], errors="coerce").fillna(0).astype(int)
            )
        totals_df = (
            df_val.loc[df_val["Vote Type"] == "Total"]
            .rename(
                columns={
                    "Precinct": "name",
                    "Voters Cast": "ballots",
                    "Registered Voters": "registered",
                    "Turnout (%)": "turnout",
                    "Over Votes": "over_votes",
                    "Under Votes": "under_votes",
                    "Total Votes": "total",
                    "Write-ins": "Write-in",
                    "McMorrow Mallory": "Mallory McMorrow",
                    "Robert Swanson Christopher": "Christopher Robert Swanson",
                    "McKinney Donavan": "Donavan McKinney",
                }
            )
            .drop("Vote Type", axis=1)
        )
        is_precinct = totals_df["name"].str.contains("Precinct", na=False)
        precinct_df = totals_df.loc[is_precinct].copy().drop(columns=["registered", "turnout"])
        precinct_df["id"] = precinct_df["name"].map(id_map)

        precinct_df.to_csv(f"{output_dir}/{race_key}.csv", index=False)

        if year == "2025":
            totals_df.loc[is_precinct, "board"] = (
                totals_df.loc[is_precinct, "name"].str.split().str[-1].map(precinct_board_map)
            )
            totals_df.loc[~is_precinct, "board"] = (
                totals_df.loc[~is_precinct, "name"].str.split().str[-1]
            )
            precinct_board_agg = (
                totals_df.drop(columns=["name", "turnout"])
                .groupby("board")
                .sum()
                .reset_index()
            )
            precinct_board_df = precinct_df[["id", "board"]].merge(
                precinct_board_agg, on="board", how="left"
            )
            precinct_board_df["turnout"] = (
                precinct_board_df["ballots"]
                .div(precinct_board_df["registered"])
                .mul(100)
                .round(2)
            )
            
            precinct_board_df.to_csv(f"{output_dir}/{race_key}-cb.csv", index=False)
