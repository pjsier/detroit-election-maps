import csv
import os
import sys
from collections import defaultdict
from pathlib import Path

def transform_row_names(race, row):
    output_row = {}
    for key, value in row.items():
        if "president-of-the-united" in race:
            if "Biden" in key:
                output_row["Joseph R. Biden Jr."] = value
                continue
            if "Williamson" in key:
                output_row["Marianne Williamson"] = value
                continue
        if "electors" in race:
            if "Trump" in key:
                output_row["Donald Trump"] = value
                continue
            elif "Kamala" in key:
                output_row["Kamala Harris"] = value
                continue
            elif "Kennedy" in key:
                output_row["Roberty F. Kennedy Jr."] = value
                continue
            elif "Kishore" in key:
                output_row["Joseph Kishore"] = value
                continue
            elif "Stein" in key:
                output_row["Jill Stein"] = value
                continue
            elif "West" in key:
                output_row["Cornel West"] = value
                continue
            elif "Oliver" in key:
                output_row["Chase Oliver"] = value
                continue
            elif "Terry" in key:
                output_row["Randall Terry"] = value
                continue
        elif "regent" in race:
            if "Ryder Diggs" in key:
                output_row["Shauna Ryder Diggs"] = value
                continue
        elif "trustee" in race:
            if "Bahar-Cook" in key:
                output_row["Rebecca Bahar-Cook"] = value
                continue
            elif "Sanger John" in key:
                output_row["John Paul Sanger"] = value
                continue
        output_row[key] = value
    return output_row


if __name__ == "__main__":
    results_dir = Path(sys.argv[1])

    county_dir_map = {}
    race_map = defaultdict(list)
    county_dirs = [
        county_dir for county_dir in results_dir.iterdir() if county_dir.is_dir()
    ]
    for county_dir in county_dirs:
        county = county_dir.stem
        county_dir_map[county] = county_dir
        for filename in county_dir.iterdir():
            race_name = filename.stem
            race_map[race_name].append(county)

    for race, counties in race_map.items():
        output_rows = []
        for county in counties:
            with Path.open(county_dir_map[county] / f"{race}.csv", "r") as f:
                output_rows.extend([transform_row_names(race, r) for r in csv.DictReader(f)])

        fieldnames = list(output_rows[0].keys())
        for key in list(output_rows[-1].keys()) + [
            "board",
            "total",
            "under_votes",
            "over_votes",
            "registered",
            "turnout",
            "ballots",
        ]:
            if key not in fieldnames:
                fieldnames.append(key)

        try:
            with Path.open(results_dir / f"{race}.csv", "w") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(output_rows)
        except ValueError as e:
            print(e)
            continue
