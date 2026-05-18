import { csvParse } from "d3-dsv"

export const getPrecinctYear = (election, year) => {
  return 2024
}

export function fetchCsvData(dataDomain, election, race, boards) {
  const [year, name] = election.split("-")
  const racePath = boards ? `${race}-cb` : race
  return fetch(`https://${dataDomain}/results/${year}/${name}/${racePath}.csv`)
    .then((data) => data.text())
    .then((data) =>
      csvParse(data).map((row) => {
        const candidates = Object.keys(row).filter(
          (k) =>
            ![
              "id",
              "board",
              "turnout",
              "registered",
              "ballots",
              "total",
              "over_votes",
              "under_votes",
            ].includes(k)
        )
        row.total = candidates.reduce((acc, curr) => acc + +row[curr], 0)
        if (+row.ballots >= 0) {
          row.total = row.ballots
        }
        candidates.forEach((candidate) => {
          row[`${candidate} Percent`] =
            Math.round((+row[candidate] / row.total || 0) * 100 * 100) / 100
          // TODO: Check turnout
        })
        return Object.entries(row)
          .map(([key, value]) => ({ [key]: key === `id` ? value : +value }))
          .reduce((acc, cur) => ({ ...acc, ...cur }), {})
      })
    )
}
