import { csvParse } from "d3-dsv"
import { BOARD_ELECTIONS, VOTE_TYPE_ELECTIONS } from "."

export const getPrecinctYear = (election, year) => {
  return year
}

export function fetchCsvData(dataDomain, election, race, voteType) {
  const year = election.split("-")[0]
  const name = election.slice(5) // Skipping over YYYY-
  let voteTypeSuffix = ``
  if (BOARD_ELECTIONS.includes(election)) {
    voteTypeSuffix = voteType === "total" ? `-cb` : ``
    if (VOTE_TYPE_ELECTIONS.includes(election) && voteType !== "total") {
      voteTypeSuffix += `-${voteType}`
    }

  } else if (voteType !== "total") {
    voteTypeSuffix = `-${voteType}`
  }
  return fetch(
    `https://${dataDomain}/results/${year}/${name}/${race}${voteTypeSuffix}.csv`
  )
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
          .map(([key, value]) => ({
            [key]: ["id", "name"].includes(key) ? value : +value,
          }))
          .reduce((acc, cur) => ({ ...acc, ...cur }), {})
      })
    )
}

export const getCity = (precinctName) =>
  precinctName.split(", ")[0].replace("City of ", "")
