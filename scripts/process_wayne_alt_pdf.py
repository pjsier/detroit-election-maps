import csv
import os
import re
import sys
import json

import pandas as pd
from collections import defaultdict
import pdfplumber
from typing import Any, DefaultDict, Dict, List, Optional, Tuple, TypedDict, Union

import pdfplumber
from pdfplumber.page import Page

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# pdfplumber itself types chars/words as Dict[str, Any] (see pdfplumber._typing.T_obj)
# and bounding boxes as a 4-tuple of numbers -- mirror those here rather than
# reaching into pdfplumber's private module.
Char = Dict[str, Any]
BBox = Tuple[float, float, float, float]

# page.crop() returns a CroppedPage, which exposes the same .chars/.find_tables()
# API as Page but isn't the same class -- accept either.
PageLike = Union[Page, "pdfplumber.page.CroppedPage"]


def slugify(text):
    return re.sub(
        r"\s", "-", re.sub(r"\s+", " ", re.sub(r"[^a-z\d]", " ", text.lower())).strip()
    ).replace("-for-", "-")


def header_text_for_cell(
    page_or_crop: PageLike,
    cell_bbox: BBox,
    space_gap: float = 1.5,
) -> str:
    """
    Reconstruct the text of one rotated header cell.

    cell_bbox: (x0, top, x1, bottom) as returned by pdfplumber's
               table.rows[...].cells
    space_gap: min vertical gap (pts) between consecutive chars in a
               rotated line to be treated as a word-space.
    """
    x0, top, x1, bottom = cell_bbox
    chars: List[Char] = [
        c
        for c in page_or_crop.chars
        if not c.get("upright", True)
        and x0 - 0.5 <= c["x0"] < x1 + 0.5
        and top - 0.5 <= c["top"] < bottom + 0.5
    ]
    if not chars:
        return ""

    # Each distinct x0 = one wrapped line of the rotated header.
    by_x: DefaultDict[float, List[Char]] = defaultdict(list)
    for c in chars:
        by_x[round(c["x0"], 1)].append(c)

    lines: List[str] = []
    for x in sorted(by_x):  # ascending x0 = left-to-right wrap order
        line_chars = sorted(by_x[x], key=lambda c: -c["top"])  # rotated reading order
        text = ""
        prev: Optional[Char] = None
        for c in line_chars:
            if prev is not None and (prev["top"] - c["bottom"]) > space_gap:
                text += " "
            text += c["text"]
            prev = c
        lines.append(text)

    return re.sub(r"\s+", " ", " ".join(lines)).strip()


def extract_race_header(page, top_cutoff=100):
    """Return the race-header text if this page starts a new race, else None."""
    words = page.extract_words(extra_attrs=["size", "fontname"])
    bold_words = [
        w
        for w in words
        if "Bold" in w["fontname"]
        and "Georgia" in w["fontname"]
        and w["top"] < top_cutoff
    ]
    if not bold_words:
        return None
    race_header_str = " ".join(
        w["text"] for w in sorted(bold_words, key=lambda w: (w["top"], w["x0"]))
    )
    return re.sub(r"\s+", " ", re.sub(r"\(.*\)", "", race_header_str)).strip()


def extract_vertical_headers(page: Page, table) -> list[str]:
    cropped = page.crop(table.bbox)
    header_row = cropped.find_tables()[0].rows[0]
    return [
        header_text_for_cell(cropped, cell) if cell else "" for cell in header_row.cells
    ]


def extract_table_info(page: Page, table) -> dict:
    # Skipping first because it's always Precinct/Vote Type
    headers = [h for h in extract_vertical_headers(page, table) if h]
    table_columns = ["Vote Type"]
    if "Times Cast" in headers:
        table_columns.extend(headers)
    else:
        for header in headers:
            table_columns.append(header)
            if "Total" not in header:
                table_columns.append(f"{header} Percent")

    precinct_map = defaultdict(list)
    precinct = ""
    table_rows = table.extract()
    # Registration at top is a bit different
    if "Voters Cast" in table_rows[0]:
        # Still skipping Precinct label
        table_columns = ["Vote Type"] + [
            re.sub(r"\s+", " ", c).strip() for c in table_rows[0][1:]
        ]

    for row in table_rows[1:]:
        if "Precinct" in row[0]:
            precinct = re.sub(r"\s+", " ", row[0]).strip()
            continue
        if (not precinct) or ("County" in row[0]) or ("top District" in row[0]):
            continue
        precinct_map[precinct].append(
            dict(zip(table_columns, [r.replace("%", "").replace(",", "") for r in row]))
        )

    return precinct_map


def process_results_input(input_file: str) -> dict:
    current_race = "Registration"
    race_mappings = {current_race: defaultdict(dict)}
    with pdfplumber.open(input_file) as pdf:
        for page in pdf.pages:
            if race_header := extract_race_header(page):
                current_race = race_header
                race_mappings[current_race] = defaultdict(dict)
            for table in page.find_tables():
                for precinct, precinct_rows in extract_table_info(page, table).items():
                    for precinct_row in precinct_rows:
                        vote_type = precinct_row.pop("Vote Type")
                        race_mappings[current_race][precinct, vote_type].update(
                            precinct_row
                        )

    return race_mappings


if __name__ == "__main__":
    input_file = sys.argv[1]
    output_dir = sys.argv[2]
    year = [val for val in output_dir.split("/") if val.isdigit()][0]
    os.makedirs(output_dir, exist_ok=True)

    with open(
        os.path.join(BASE_DIR, "data", "precincts", f"map-{year}.json"), "r"
    ) as f:
        id_map = json.load(f)

    processed_results = process_results_input(input_file)
    for race_key, race_results in processed_results.items():
        output_results = []
        for precinct_key, precinct_data in race_results.items():
            # TODO: Currently filtering out Detroit, later on we can join to state dataset
            # if "Detroit" not in precinct_key[0]:
            #     continue
            # TODO: Can split out in future
            if precinct_key[1] != "Total":
                continue

            precinct_data["registered"] = int(
                precinct_data.pop("Registered Voters", "")
            )
            precinct_data["ballots"] = int(precinct_data.pop("Times Cast", "0"))
            precinct_data["over_votes"] = "0"
            precinct_data["under_votes"] = "0"
            precinct_data["total"] = precinct_data.pop("Total Votes", "")
            precinct_data["turnout"] = round(
                (precinct_data["ballots"] / precinct_data["registered"]) * 100, 2
            )
            if "Voters Cast" in precinct_data:
                precinct_data["ballots"] = int(precinct_data.pop("Voters Cast", "0"))
            if "% Turnout" in precinct_data:
                precinct_data["turnout"] = precinct_data.pop("% Turnout", "")
            precinct_data_keys = list(precinct_data.keys())
            for precinct_data_key in precinct_data_keys:
                if " Percent" in precinct_data_key:
                    precinct_data.pop(precinct_data_key, None)
                elif "(" in precinct_data_key:
                    clean_key = re.sub(r"\s\(.*\)", "", precinct_data_key)
                    precinct_data[clean_key] = precinct_data.pop(precinct_data_key)

            output_results.append(
                {
                    "id": id_map[precinct_key[0]],
                    "name": precinct_key[0],
                    "board": "",
                    **precinct_data,
                }
            )
        if len(output_results) == 0:
            continue
        with open(f"{output_dir}/{slugify(race_key)}.csv", "w") as f:
            writer = csv.DictWriter(f, output_results[0].keys())
            writer.writeheader()
            writer.writerows(output_results)
