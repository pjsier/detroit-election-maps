import { csvParse } from "d3-dsv"

const BOARD_YEARS = [2025]

export const getPrecinctYear = (election, year) => {
  return year
}

export function fetchCsvData(dataDomain, election, race, boards) {
  const [year, name] = election.split("-")
  const racePath = boards && BOARD_YEARS.includes(+year) ? `${race}-cb` : race
  return fetch(`https://${dataDomain}/results/${year}/${name}/${racePath}.csv`)
    .then((data) => data.text())
    .then((data) =>
      csvParse(data).map((row) => {
        const candidates = Object.keys(row).filter(
          (k) =>
            ![
              "id",
              "name",
              "board",
              "turnout",
              "registered",
              "ballots",
              "total",
              "over_votes",
              "under_votes",
            ].includes(k) && !k.includes(" Percent")
        )
        row.total = candidates.reduce((acc, curr) => acc + +row[curr], 0)
        candidates.forEach((candidate) => {
          if (
            !row[`${candidate} Percent`] ||
            row[`${candidate} Percent`] === Infinity
          ) {
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
