import { csvParse } from "d3-dsv"

export const getPrecinctYear = (election, year) => {
  return 2024
}

export function fetchCsvData(dataDomain, election, race) {
  const [year, name] = election.split("-")
  return fetch(`https://${dataDomain}/results/${year}/${name}/${race}.csv`)
    .then((data) => data.text())
    .then((data) =>
      csvParse(data).map((row) => {
        // TODO: Is this correct?
        const candidates = Object.keys(row).filter((k) => k !== "id")
        row.total = candidates.reduce((acc, curr) => acc + +row[curr], 0)
        if (row.ballots >= 0) {
          row.total = row.ballots
        }
        candidates.forEach((candidate) => {
          if (!row.ballots) {
            row[`${candidate} Percent`] =
              Math.round((+row[candidate] / row.total || 0) * 100 * 100) / 100
          }
        })
        return Object.entries(row)
          .map(([key, value]) => ({ [key]: key === `id` ? value : +value }))
          .reduce((acc, cur) => ({ ...acc, ...cur }), {})
      })
    )
}
