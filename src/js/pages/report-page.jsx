import { createEffect, createMemo, onCleanup, For } from "solid-js"
import { createStore } from "solid-js/store"
import { csvFormat } from "d3-dsv"
import { getColor } from "../utils/map"
import {
  descending,
  updateQueryParams,
  VOTE_TYPE_YEARS,
  BOARD_YEARS,
  VOTE_TYPE_OPTIONS,
} from "../utils"
import { fetchCsvData, getCity } from "../utils/data"

const ReportPage = (props) => {
  const [state, setState] = createStore({
    election: props.initialElection,
    race: props.initialRace,
    voteType: props.initialVoteType,
    city: props.initialCity,
    url: ``,
    data: [],
  })
  createEffect(() => {
    updateQueryParams({
      election: state.election,
      race: state.race,
      voteType: state.voteType,
      city: state.city,
    })
  })

  const year = createMemo(() => props.elections[state.election].year)
  const boards = createMemo(
    () => props.voteType === "total" && BOARD_YEARS.includes(+year())
  )
  const dataResults = createMemo(() => {
    console.log(state.city)
    return state.data.filter(({ name }) =>
      !!state.city ? getCity(name) === state.city : true
    )
  })
  const dataColumns = createMemo(() =>
    state.data.length > 0 ? Object.keys(state.data[0]) : []
  )
  const tableColumns = createMemo(() => [
    "name",
    "ballots",
    ...dataColumns().filter((col) => col.includes("Percent")),
  ])
  const cities = createMemo(() =>
    [
      ...new Set(state.data.map(({ name }) => (name ? getCity(name) : ``))),
    ].sort()
  )
  const candidates = createMemo(() => {
    const candidateNames = dataColumns()
      .filter((row) => row.includes("Percent"))
      .map((c) => c.replace(" Percent", ""))
    const aggBase = {
      total: 0,
      ...candidateNames.reduce((a, v) => ({ ...a, [v]: 0 }), {}),
    }
    let electionResults = aggBase
    // TODO: If board is blank then ignore this?
    if (boards()) {
      const countingBoards = []
      data.forEach((row) => {
        if (countingBoards.includes(row.board)) return
        Object.keys(aggBase).forEach((key) => {
          electionResults[key] += row[key]
        })
        countingBoards.push(row.board)
      })
    } else {
      electionResults = dataResults().reduce(
        (agg, val) =>
          Object.keys(agg).reduce(
            (a, v) => ({
              ...a,
              total: agg.total + val[v],
              [v]: agg[v] + val[v],
            }),
            {}
          ),
        aggBase
      )
    }
    const candidates = candidateNames
      .filter((name) => !["ballots", "registered"].includes(name))
      .map((name, idx) => ({
        name,
        color: getColor(name, idx),
        votes: electionResults[name === "turnout" ? "total" : name],
      }))
      .sort((a, b) => descending(a.votes, b.votes))
    return candidates
  })

  const raceTotal = createMemo(() =>
    candidates().reduce((acc, { votes }) => acc + votes, 0)
  )
  const raceOptions = createMemo(() =>
    Object.entries(props.elections[state.election].races).map(
      ([value, label]) => ({ label, value })
    )
  )
  const voteTypeOptions = createMemo(() =>
    BOARD_YEARS.includes(+year())
      ? VOTE_TYPE_OPTIONS.filter(({ value }) => value !== "all-early-votes")
      : VOTE_TYPE_OPTIONS
  )

  // Based on solidjs/solid/issues/670#issuecomment-930346644
  // eslint-disable-next-line solid/reactivity
  createEffect(async () => {
    let canceled = false
    onCleanup(() => (canceled = true))

    const csvData = await fetchCsvData(
      props.dataDomain,
      state.election,
      state.race,
      state.voteType
    )
    if (canceled) return

    setState({ data: csvData })
    let blob = new Blob([csvFormat(csvData)], { type: "text/csv;charset=utf8" })

    setState({
      url: window.URL.createObjectURL(blob),
    })
  })

  return (
    <>
      <div class="report-content">
        <form method="GET" action="">
          <label for="election">Election</label>
          <div class="select mb-3">
            <select
              id="election"
              name="election"
              value={state.election}
              onChange={(e) => {
                const election = e.target.value
                const selectedRaceLabel = raceOptions().find(
                  ({ value }) => value === state.race
                )?.label
                const raceNameMap = Object.entries(
                  props.elections[election].races
                ).reduce(
                  (acc, [value, label]) => ({ ...acc, [label]: value }),
                  {}
                )

                // Replicating pattern from MapPage
                setState({ election, race: "turnout", city: "" })
                if (raceNameMap[selectedRaceLabel]) {
                  setState({ race: raceNameMap[selectedRaceLabel] })
                }
              }}
            >
              <For each={props.electionOptions}>
                {({ label, value }) => <option value={value}>{label}</option>}
              </For>
            </select>
          </div>
          <label for="race">Race</label>
          <div class="select mb-3">
            <select
              id="race"
              name="race"
              aria-label="Race"
              value={state.race}
              onChange={(e) => setState({ race: e.target.value, city: "" })}
            >
              <For each={raceOptions()}>
                {({ label, value }) => <option value={value}>{label}</option>}
              </For>
            </select>
          </div>
          <label for="city">City</label>
          <div class="select mb-3">
            <select
              id="city"
              name="city"
              aria-label="City"
              value={state.city}
              onChange={(e) => setState({ city: e.target.value })}
            >
              <option></option>
              <For each={cities()}>
                {(city) => <option value={city}>{city}</option>}
              </For>
            </select>
          </div>
          <Show
            when={
              VOTE_TYPE_YEARS.includes(+year()) &&
              !(+year() === 2026 && state.race === "turnout")
            }
          >
            <label for="race">Race</label>
            <div class="select mb-3">
              <select
                id="vote-type"
                name="vote-type"
                aria-label="Vote Type"
                value={state.voteType}
                onChange={(e) => setState({ voteType: e.target.value })}
              >
                <For each={voteTypeOptions()}>
                  {({ label, value }) => <option value={value}>{label}</option>}
                </For>
              </select>
            </div>
          </Show>
        </form>
        <div>
          <For each={candidates()}>
            {({ name, votes }) => (
              <div class="legend-row">
                <div class="legend-row-details">
                  <span class="label">
                    <strong>{name}</strong>
                  </span>
                </div>
                <div class="numbers">
                  <div class={props.race === "turnout" ? "hidden" : ""}>
                    {votes.toLocaleString()}
                  </div>
                  <Show when={!isNaN(votes / raceTotal())}>
                    <div class="percent">
                      {((votes / raceTotal()) * 100)
                        .toFixed(1)
                        .replace("100.0", "100")}
                      %
                    </div>
                  </Show>
                </div>
              </div>
            )}
          </For>
        </div>
        <a
          href={state.url}
          download={`election-data-${state.election}-${state.race}.csv`}
          class="download-button"
        >
          Download file
        </a>
      </div>
      <div class="table-container">
        <table>
          <thead>
            <For each={tableColumns()}>
              {(col) => <th>{col.replace(" Percent", "")}</th>}
            </For>
          </thead>
          <tbody>
            <For each={dataResults()}>
              {(row) => (
                <tr>
                  <For each={tableColumns()}>
                    {(col) => (
                      <td>
                        {row[col]}
                        {col.includes(" Percent") ? "%" : ``}
                      </td>
                    )}
                  </For>
                </tr>
              )}
            </For>
          </tbody>
        </table>
      </div>
    </>
  )
}

export default ReportPage
