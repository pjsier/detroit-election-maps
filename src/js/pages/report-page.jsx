import { createEffect, createMemo, onCleanup, For } from "solid-js"
import { createStore } from "solid-js/store"
import { csvFormat } from "d3-dsv"
import { getColor } from "../utils/map"
import {
  descending,
  updateQueryParams,
  VOTE_TYPE_ELECTIONS,
  BOARD_ELECTIONS,
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
    () => state.voteType === "total" && BOARD_ELECTIONS.includes(state.election)
  )
  const dataResults = createMemo(() => {
    return state.data.filter(({ name }) =>
      !!state.city ? getCity(name) === state.city : true
    )
  })
  const boardResults = createMemo(() => {
    if (!boards()) {
      return dataResults()
    }
    let boardNames = []
    let results = []
    dataResults().forEach((row) => {
      if (!!row.board && boardNames.includes(row.board)) return
      results.push(row)
      boardNames.push(row.board)
    })
    return results
  })
  const dataColumns = createMemo(() =>
    state.data.length > 0 ? Object.keys(state.data[0]) : []
  )
  const tableColumns = createMemo(() =>
    state.race === "turnout"
      ? ["name", "ballots", "registered", "turnout"]
      : ["name", ...dataColumns().filter((col) => col.includes("Percent"))]
  )
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
    if (boards()) {
      const countingBoards = []
      dataResults().forEach((row) => {
        if (!!row.board && countingBoards.includes(row.board)) return
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
        color: getColor(name, state.election, idx),
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
  const turnoutTotals = createMemo(() => {
    if (state.race !== "turnout") return {}
    const ballots = dataResults()
      .map(({ ballots }) => ballots)
      .reduce((acc, curr) => acc + curr, 0)
    const registered = dataResults()
      .map(({ registered }) => registered)
      .reduce((acc, curr) => acc + curr, 0)

    return {
      ballots,
      turnout: ((ballots / registered) * 100)
        .toFixed(2)
        .replace("100.0", "100"),
    }
  })
  const voteTypeOptions = createMemo(() =>
    BOARD_ELECTIONS.includes(state.election)
      ? VOTE_TYPE_OPTIONS.filter(({ value }) => value !== "all-early-votes")
      : VOTE_TYPE_OPTIONS
  )

  const tableCellContent = (col, row) => {
    if (col === "name") {
      return boards() ? `Counting Board ${row.board}` : `Precinct ${row.id}`
    }
    return `${row[col]} ${col.includes(" Percent") ? "%" : ``}`
  }

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
          <Show when={year() !== 2025}>
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
          </Show>
          <Show
            when={
              VOTE_TYPE_ELECTIONS.includes(state.election) &&
              !(+year() === 2026 && state.race === "turnout")
            }
          >
            <label for="vote-type">Vote type</label>
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
        <div class="legend-report">
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
          <div class="legend-row">
            <div class="legend-row-details">
              <span class="label">
                <strong>Total</strong>
              </span>
            </div>
            <div class="numbers">
              <Show
                when={state.race === "turnout"}
                fallback={
                  <div>
                    <strong>{raceTotal().toLocaleString()}</strong>
                  </div>
                }
              >
                <div>{turnoutTotals().ballots.toLocaleString()}</div>
                <div class="percent">{turnoutTotals().turnout}%</div>
              </Show>
            </div>
          </div>
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
            <For each={boards() ? boardResults() : dataResults()}>
              {(row) => (
                <tr>
                  <For each={tableColumns()}>
                    {(col) => (
                      <td>
                        {tableCellContent(col, row)}
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
