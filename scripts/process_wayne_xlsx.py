import csv
import os
import re
import sys
import json
from collections import defaultdict

import openpyxl
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Rows in each contest sheet whose first cell is one of these hold vote data
# for the most recently seen precinct label row.
VOTE_TYPES = {
    "Early Voting",
    "Election Day",
    "Absentee",
    "Pre-Process Absentee",
    "Total",
}
# Rows that only introduce the table, not a precinct
SKIP_LABELS = {"County", "Wayne County"}
CONTEST_TOTAL_LABEL = "County - Total"


def is_counting_board_election(output_dir: str) -> bool:
    return ("2025" in output_dir) or (("2024" in output_dir) and (("presidential" in output_dir) or ("general" in output_dir))) or (("2026" in output_dir) and ("general" in output_dir))


def slugify(text):
    return re.sub(
        r"\s", "-", re.sub(r"\s+", " ", re.sub(r"[^a-z\d]", " ", text.lower())).strip()
    )


def clean_header(header):
    """
    Excel headers look like "Abdul El-Sayed\\n(DEM) " or "Write-in\\n ".
    Drop the trailing party tag and collapse whitespace.
    """
    header = re.sub(r"\s*\([A-Za-z]{2,4}\)\s*$", "", str(header).strip())
    return re.sub(r"\s+", " ", header).strip()


def party_tag(header):
    m = re.search(r"\(([A-Za-z]{2,4})\)\s*$", str(header).strip())
    return m.group(1) if m else ""


def ordinal(n):
    n = int(n)
    suffix = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def normalize_district_title(title):
    """
    "Representative in Congress District 13" -> "Representative in Congress 13th District"
    (same wording the State Representative sheets already use)
    """
    return re.sub(
        r"^(Representative in Congress|State Senator) District (\d+)\b",
        lambda m: f"{m.group(1)} {ordinal(m.group(2))} District",
        title,
        flags=re.I,
    )


def extract_race_title(ws_rows):
    """Contest title lives in A2, e.g. "United States Senator (Vote for  1)   "."""
    if len(ws_rows) < 2 or not ws_rows[1][0]:
        return None
    title = re.sub(r"\(\s*Vote\s+for\s+\d+\s*\)", "", str(ws_rows[1][0]), flags=re.I)
    title = normalize_district_title(re.sub(r"\s+", " ", title).strip())
    title = slugify(title) or None
    title = title.replace("state-representative-", "representative-in-state-legislature-").replace("state-senator-", "representative-in-state-senate-")
    return title


def extract_sheet_table(ws_rows, label_cols=("Precinct", "Vote Type")):
    """
    Parse one contest sheet into (DataFrame, contest_total_dict).

    Layout (0-indexed columns):
      A = precinct / vote type label, B = Times Cast, C = Registered Voters,
      E = label repeated, F.. = candidate columns (with blank spacer columns),
      header on the row whose first cell is "Precinct".
    """
    header_idx = next(
        (i for i, r in enumerate(ws_rows[:10]) if r and r[0] == "Precinct"), None
    )
    if header_idx is None:
        return None, None
    header = ws_rows[header_idx]

    # Every non-empty header cell except the two "Precinct" label columns is data
    data_cols = [
        i
        for i, v in enumerate(header)
        if v not in (None, "") and str(v).strip() != "Precinct"
    ]
    if len(data_cols) <= 2:  # only Times Cast / Registered, no contest columns
        return None, None

    raw_headers = [header[i] for i in data_cols]
    col_names = [clean_header(h) for h in raw_headers]
    # Same name twice in a contest (e.g. one person on two party lines): keep party
    seen = defaultdict(int)
    for n in col_names:
        seen[n] += 1
    col_names = [
        f"{n} ({party_tag(h)})" if seen[n] > 1 and party_tag(h) else n
        for n, h in zip(col_names, raw_headers)
    ]

    records = []
    contest_total = None
    current_precinct = ""
    for row in ws_rows[header_idx + 1 :]:
        label = row[0]
        if label in (None, ""):
            continue
        label = str(label).strip()

        if label in VOTE_TYPES:
            values = [row[i] if i < len(row) else None for i in data_cols]
            records.append([current_precinct, label] + values)
        elif label == CONTEST_TOTAL_LABEL:
            contest_total = {
                n: row[i] if i < len(row) else None for n, i in zip(col_names, data_cols)
            }
        elif label.endswith(" - Total") or label in SKIP_LABELS:
            continue
        else:
            current_precinct = label

    df = pd.DataFrame(records, columns=list(label_cols) + col_names)
    return df, contest_total


def build_board_df(vote_type_df, registered_df, id_map, precinct_board_map, label):
    df = vote_type_df.drop(columns=["registered", "turnout"], errors="ignore").merge(
        registered_df, on="name", how="left"
    )
    df["registered"] = df["registered"].fillna(0)

    board_ids = set(precinct_board_map.values())
    last_token = df["name"].astype(str).str.split().str[-1]
    is_precinct = df["name"].str.contains("Precinct", na=False)
    is_detroit = df["name"].str.contains("Detroit", na=False)

    is_cb_precinct = is_precinct & is_detroit
    # Counting-board rows: non-precinct Detroit rows whose last token is a known board
    is_cb_row = (~is_precinct) & is_detroit & last_token.isin(board_ids)

    df["board"] = ""
    df.loc[is_cb_precinct, "board"] = last_token[is_cb_precinct].map(precinct_board_map)
    df.loc[is_cb_row, "board"] = last_token[is_cb_row]
    df["board"] = df["board"].fillna("")
    has_board = df["board"] != ""

    missing = df.loc[is_cb_precinct & ~has_board, "name"]
    if not missing.empty:
        print(f"{label}: no counting board for {list(missing)}")

    # Aggregation key: shared per board, unique per unmatched precinct,
    # None (dropped from the sum) for everything else (Contest Total, other jurisdictions' non-precinct rows)
    df["_key"] = None
    df.loc[has_board, "_key"] = "board:" + df.loc[has_board, "board"]
    unmatched = is_precinct & ~has_board
    df.loc[unmatched, "_key"] = "name:" + df.loc[unmatched, "name"]

    board_agg = df.drop(columns=["name", "board"]).groupby("_key", as_index=False).sum()

    precincts = df.loc[is_precinct, ["name", "board", "_key"]].copy()
    precincts["id"] = precincts["name"].map(id_map)
    out = precincts[["id", "name", "board", "_key"]].merge(board_agg, on="_key", how="left")
    out = out.drop(columns="_key")
    out["turnout"] = (
        out["ballots"].div(out["registered"]).mul(100).round(2)
        .replace(float("inf"), float("nan"))
    )
    return out


def write_turnout(df, id_map, precinct_board_map, output_dir, unmapped):
    """
    Write turnout.csv (and turnout-cb.csv for counting-board elections) from the
    Stats sheet's "Total" rows: id, name, ballots, registered, turnout.
    """
    df = df.loc[df["Vote Type"] == "Total", ["Precinct", "Voters Cast", "Registered Voters"]]
    df = df.rename(
        columns={
            "Precinct": "name",
            "Voters Cast": "ballots",
            "Registered Voters": "registered",
        }
    ).copy()
    for col in ("ballots", "registered"):
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
    registered_df = df[["name", "registered"]].drop_duplicates("name")

    is_precinct = df["name"].str.contains("Precinct", na=False)
    out = df.loc[is_precinct].copy()
    out["id"] = out["name"].map(id_map)
    unmapped.update(out.loc[out["id"].isna(), "name"])
    out["turnout"] = (
        out["ballots"].div(out["registered"]).mul(100).round(2)
        .replace(float("inf"), float("nan"))
    )
    out[["id", "name", "ballots", "registered", "turnout"]].to_csv(
        f"{output_dir}/turnout.csv", index=False
    )

    if is_counting_board_election(output_dir):
        build_board_df(
            df, registered_df, id_map, precinct_board_map, "turnout"
        ).to_csv(f"{output_dir}/turnout-cb.csv", index=False)


def assert_totals_match(race_name, df, contest_total):
    """
    Sum of each precinct's "Total" row must equal the sheet's "County - Total" row,
    for both ballots cast and total votes (when the contest has that column).
    """
    if contest_total is None:
        print(f"{race_name}: no contest total row to check against")
        return
    total_rows = df.loc[df["Vote Type"] == "Total"]
    for col in ("Times Cast", "Voters Cast", "Total Votes"):
        if col not in df.columns:
            continue
        summed = (
            pd.to_numeric(total_rows[col], errors="coerce").fillna(0).astype(int).sum()
        )
        expected = int(pd.to_numeric(contest_total.get(col), errors="coerce") or 0)
        assert summed == expected, f"{race_name} {col}: {summed} != {expected}"
    print(f"{race_name} totals match")


if __name__ == "__main__":
    input_file = sys.argv[1]
    output_dir = sys.argv[2]
    year = [val for val in output_dir.split("/") if val.isdigit()][0]

    os.makedirs(output_dir, exist_ok=True)

    with open(
        os.path.join(BASE_DIR, "data", "precincts", f"map-{year}.json"), "r"
    ) as f:
        id_map = {k: str(int(v)) for k, v in json.load(f).items()}

    df_map: dict[str, pd.DataFrame] = {}
    contest_totals: dict[str, dict] = {}
    precinct_board_map = {}
    turnout_df, turnout_total = None, None

    # Group sheets by race title in case a race is split across multiple sheets
    label_cols = {"Precinct", "Vote Type"}
    batch_frames: dict[str, dict[frozenset, pd.DataFrame]] = defaultdict(dict)

    wb = openpyxl.load_workbook(input_file, read_only=True, data_only=True)
    for idx, ws in enumerate(wb.worksheets):
        rows = list(ws.iter_rows(values_only=True))
        title = extract_race_title(rows)
        if title is None:
            # The Stats sheet (page 1) has registered voters / voters cast per precinct
            stats_df, stats_total = extract_sheet_table(rows)
            if stats_df is not None and "Voters Cast" in stats_df.columns:
                turnout_df, turnout_total = stats_df, stats_total
            else:  # Table of Contents, ...
                print(idx, ws.title, "(skipped)")
            continue
        df, contest_total = extract_sheet_table(rows)
        if df is None:
            print(idx, ws.title, "(no table)")
            continue
        contest_totals.setdefault(title, contest_total)

        batches = batch_frames[title]
        batch_key = frozenset(df.columns) - label_cols
        if batch_key in batches:
            batches[batch_key] = pd.concat(
                [batches[batch_key], df], axis=0, ignore_index=True
            )
        else:
            batches[batch_key] = df
    wb.close()

    for title, batches in batch_frames.items():
        batch_dfs = list(batches.values())
        merged = batch_dfs[0]
        for other in batch_dfs[1:]:
            diff_cols = [c for c in other.columns if c not in merged.columns]
            df_to_merge = other[["Precinct", "Vote Type"] + diff_cols]
            merged = pd.merge(
                merged, df_to_merge, on=["Precinct", "Vote Type"], how="left"
            )
        df_map[title] = merged

    for race_key, df_val in df_map.items():
        assert_totals_match(race_key, df_val, contest_totals.get(race_key))

    if is_counting_board_election(output_dir):
        with open(
            os.path.join(BASE_DIR, "data", "counting-boards", f"{year}.csv"), "r"
        ) as f:
            reader = csv.DictReader(f)
            precinct_board_map = {r["precinct"]: r["board"] for r in reader}

    unmapped = set()
    for race_key, df_val in df_map.items():
        df_val = df_val.loc[:, ~df_val.columns.duplicated()].copy()
        for col in df_val.columns:
            if col in ["Precinct", "Vote Type", "Turnout (%)"]:
                continue
            df_val[col] = (
                pd.to_numeric(df_val[col], errors="coerce").fillna(0).astype(int)
            )
        df_val = df_val.rename(
            columns={
                "Precinct": "name",
                "Times Cast": "ballots",
                "Registered Voters": "registered",
                "Turnout (%)": "turnout",
                "Over Votes": "over_votes",
                "Under Votes": "under_votes",
                "Total Votes": "total",
                "Write-ins": "Write-in",
            }
        )
        registered_df = (
            df_val.loc[df_val["Vote Type"] == "Total", ["name", "registered"]]
            .drop_duplicates("name")
        )

        vote_types = [vt for vt in list(df_val["Vote Type"].unique()) if vt] + [
            "All Early Votes"
        ]
        for vote_type in vote_types:
            if vote_type == "All Early Votes":
                vote_type_df = df_val.loc[
                    ~df_val["Vote Type"].isin(["Total", "Election Day"])
                ].drop("Vote Type", axis=1)
                vote_type_df = vote_type_df.groupby("name", as_index=False).sum()
            else:
                vote_type_df = df_val.loc[df_val["Vote Type"] == vote_type].drop(
                    "Vote Type", axis=1
                )
            is_precinct = vote_type_df["name"].str.contains("Precinct", na=False)
            vote_type_precinct_df = (
                vote_type_df.loc[is_precinct]
                .copy()
                .drop(columns=["registered", "turnout"], errors="ignore")
            )
            vote_type_precinct_df["id"] = vote_type_precinct_df["name"].map(id_map)
            unmapped.update(
                vote_type_precinct_df.loc[vote_type_precinct_df["id"].isna(), "name"]
            )
            vote_type_suffix = ""
            if vote_type != "Total":
                vote_type_suffix = f"-{slugify(vote_type)}"
            vote_type_precinct_df.to_csv(
                f"{output_dir}/{race_key}{vote_type_suffix}.csv", index=False
            )

            if is_counting_board_election(output_dir):
                build_board_df(
                    vote_type_df, registered_df, id_map, precinct_board_map,
                    f"{race_key}{vote_type_suffix}",
                ).to_csv(f"{output_dir}/{race_key}{vote_type_suffix}-cb.csv", index=False)

    if turnout_df is not None:
        assert_totals_match("turnout", turnout_df, turnout_total)
        write_turnout(turnout_df, id_map, precinct_board_map, output_dir, unmapped)
    else:
        print("No Stats sheet found; turnout.csv not written")

    if unmapped:
        print(f"{len(unmapped)} precinct names missing from map-{year}.json:")
        for name in sorted(unmapped):
            print("  ", name)
