import re
import sys

import pandas as pd
import pdfplumber


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
    return headers, header_bottom, col_centers


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

    return slugify(race_title)


def extract_page_table(page, label_cols=("Precinct", "Vote Type")):
    col_headers, header_bottom, col_centers = get_rotated_headers(page)
    if not col_headers:
        return None

    rotated_x_start = min(col_centers)

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
        label_words = [w for w in row if w["x1"] < rotated_x_start - 10]
        data_word_list = [w for w in row if w["x0"] >= rotated_x_start - 10]
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

    return pd.DataFrame(records, columns=all_headers)


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

    df_list: list[pd.DataFrame] = []
    df_map: dict[str, pd.DataFrame] = {}

    with pdfplumber.open(input_file) as pdf:
        for idx, page in enumerate(pdf.pages):
            title = extract_race_title(page)
            df = extract_page_table(page)
            if title is None:
                print(idx, df.columns)

            if title in df_map and df_map[title].columns.equals(df.columns):
                if df_map[title].columns.equals(df.columns):
                    df_map[title] = pd.concat(
                        [df_map[title], df], axis=0, ignore_index=True
                    )

            else:
                df_map[title] = df

    for race_key, df_val in df_map.items():
        assert_totals_match(race_key, df_val)
        df_val.to_csv(f"{output_dir}/{race_key}.csv", index=False)
