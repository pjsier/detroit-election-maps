"""
Start with <VoterTurnout
Iterate through contests, write each individually,
build rows separately for candidates, combine keys based on precinct?
"""

import os
from lxml import etree
import csv
import sys
from collections import defaultdict
import re
import json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def slugify(text):
    slug_text = re.sub(
        r"\s", "-", re.sub(r"\s+", " ", re.sub(r"[^a-z\d]", " ", text.lower())).strip()
    ).replace("-for-", "-")
    if slug_text.startswith("dem-"):
        return f"{slug_text[4:]}-dem"
    if slug_text.startswith("rep-"):
        return f"{slug_text[4:]}-rep"
    return slug_text


def clean_precinct_name(precinct_name):
    return (
        precinct_name.replace(" Twp, ", " Township, ")
        .replace(" Pct ", " Precinct ")
        .replace(
            "Grosse Pointe Shores, ",
            "Village of Grosse Pointe Shores, A Michigan City, ",
        )
        .replace("Richmond City, ", "Richmond, ")
        .replace("Shelby Township, ", "Shelby Charter Township, ")
    )


def clean_candidate_name(candidate_name):
    return candidate_name.replace(",", "")


def parse_voter_turnout(tree, id_map):
    results = []
    for precinct in tree.xpath(".//VoterTurnout/Precincts/Precinct"):
        precinct_name = clean_precinct_name(precinct.attrib["name"])
        if precinct_name not in id_map:
            print(precinct_name)
            continue
        results.append(
            {
                "id": id_map[precinct_name],
                "name": precinct_name,
                "ballots": precinct.attrib["ballotsCast"],
                "registered": precinct.attrib["totalVoters"],
                "turnout": precinct.attrib["voterTurnout"],
            }
        )
    return results


def process_contest(contest, id_map):
    precinct_map = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    for choice in contest.xpath("./Choice"):
        for vote_type in choice.xpath("./VoteType"):
            for precinct in vote_type.xpath("./Precinct"):
                vote_type_name = vote_type.attrib["name"].split(" - ")[0]
                precinct_name = clean_precinct_name(precinct.attrib["name"])
                precinct_map[precinct_name][vote_type_name][
                    clean_candidate_name(choice.attrib["text"])
                ] += int(precinct.attrib["votes"])
                if vote_type_name not in ["Election", "Election Day"]:
                    precinct_map[precinct_name]["All Early Votes"][
                        clean_candidate_name(choice.attrib["text"])
                    ] += int(precinct.attrib["votes"])

                precinct_map[precinct_name]["Total"][
                    clean_candidate_name(choice.attrib["text"])
                ] += int(precinct.attrib["votes"])

    precinct_vote_type_map = defaultdict(list)
    missing_precincts = set()
    for precinct, vote_type_results in precinct_map.items():
        for vote_type, results in vote_type_results.items():
            total = sum(results.values())
            write_ins = 0
            results_keys = list(results.keys())
            for results_key in results_keys:
                if "rite-in" in results_key:
                    write_ins += results.pop(results_key)
            if precinct not in id_map:
                print(precinct)
                continue
            precinct_vote_type_map[vote_type].append(
                {
                    "id": id_map[precinct],
                    "name": precinct,
                    "total": total,
                    # Including these not to break join, but would have to be pulled separately
                    "over_votes": "",
                    "under_votes": "",
                    "Write-in": write_ins,
                    **results,
                }
            )
    return contest.attrib["text"], precinct_vote_type_map


if __name__ == "__main__":
    output_dir = sys.argv[2]
    year = [val for val in output_dir.split("/") if val.isdigit()][0]
    os.makedirs(output_dir, exist_ok=True)

    with open(
        os.path.join(BASE_DIR, "data", "precincts", f"map-{year}.json"), "r"
    ) as f:
        id_map = json.load(f)

    with open(sys.argv[1], "r") as f:
        tree = etree.fromstring(f.read().encode())

    turnout_rows = parse_voter_turnout(tree, id_map)
    with open(os.path.join(output_dir, "turnout.csv"), "w") as f:
        writer = csv.DictWriter(f, fieldnames=list(turnout_rows[0].keys()))
        writer.writeheader()
        writer.writerows(turnout_rows)

    for contest in tree.xpath(".//Contest"):
        contest_name, contest_row_map = process_contest(contest, id_map)
        if "delegate-to-county-convention" in slugify(contest_name):
            continue

        for vote_type, rows in contest_row_map.items():
            if len(rows) == 0:
                continue
            vote_type_suffix = ""
            if vote_type != "Total":
                vote_type_suffix = (
                    "-election-day"
                    if vote_type == "Election"
                    else f"-{slugify(vote_type)}"
                )
            with open(
                os.path.join(
                    output_dir, f"{slugify(contest_name)}{vote_type_suffix}.csv"
                ),
                "w",
            ) as f:
                writer = csv.DictWriter(
                    f, fieldnames=list(contest_row_map[vote_type][0].keys())
                )
                writer.writeheader()
                writer.writerows(contest_row_map[vote_type])
