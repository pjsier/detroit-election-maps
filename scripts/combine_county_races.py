import csv
import os
import sys
from collections import defaultdict
from pathlib import Path

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
                # TODO: Have to streamline candidate names
                output_rows.extend([r for r in csv.DictReader(f)])

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
