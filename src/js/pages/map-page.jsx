import { For, Show, createEffect, createMemo } from "solid-js"
import { createStore } from "solid-js/store"
import Map from "../components/map"
import Legend from "../components/legend"
import Popup from "../components/popup"
import PopupContent from "../components/popup-content"
import Geocoder from "../components/geocoder"
import { useMapStore } from "../providers/map"
import { usePopup } from "../providers/popup"
import { updateQueryParams } from "../utils"
import { getPrecinctYear } from "../utils/data"
import mapStyle from "../mapStyle"

const EMBED_MOBILE_CUTOFF = 500
const MOBILE_CUTOFF = 800

const UNOFFICIAL_RESULTS = ["2025-primary"]

const MapPage = (props) => {
  const [state, setState] = createStore({
    election: props.initialElection,
    race: props.initialRace,
  })
  const [mapStore] = useMapStore()
  const [popup, setPopup] = usePopup()
  createEffect(() => {
    updateQueryParams({
      election: state.election,
      race: state.race,
    })
  })

  const year = createMemo(() => props.elections[state.election].year)
  const raceOptions = createMemo(() =>
    Object.entries(props.elections[state.election].races).map(
      ([value, label]) => ({ label, value })
    )
  )

  const isEmbedded = document.documentElement.classList.contains("embedded")
  const isMobile =
    window.innerWidth < (isEmbedded ? EMBED_MOBILE_CUTOFF : MOBILE_CUTOFF)

  const mapViewOptions = isMobile
    ? { zoom: 9, center: [-83.0983, 42.3368] }
    : { zoom: 9.5, center: [-83.0983, 42.401] }

  return (
    <>
      <Map
        dataDomain={props.dataDomain}
        year={year()}
        election={state.election}
        race={state.race}
        isMobile={isMobile}
        mapOptions={{
          style: mapStyle,
          minZoom: 8,
          maxZoom: 15,
          hash: true,
          dragRotate: false,
          attributionControl: false,
          maxBounds: [-84.158, 41.723, -82.375, 43.168],
          ...mapViewOptions,
        }}
      />
      <div id="legend">
        <div id="geocoder-container">
          <Geocoder
            azureMapsKey={props.azureMapsKey}
            onSelect={(selectedPoint) => setPopup({ selectedPoint })}
          />
        </div>
        <div class="content">
          <h1>
            {props.embedElection
              ? props.elections[state.election].label
              : "Detroit Election Maps"}
          </h1>
          <form method="GET" action="">
            <Show when={!props.embedElection}>
              <div class="select">
                <select
                  aria-label="Election"
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
                    setState({
                      election,
                      race: "0",
                    })
                    // This is a workaround for the fact that sometimes the
                    // race IDs are the same between two elections, which
                    // doesn't force a state update and causes issues with
                    // <select>. We're force-resetting the race above and
                    // then changing it here to make sure it's applied, and
                    // it's fast enough to not cause a UI flicker
                    if (raceNameMap[selectedRaceLabel]) {
                      setState({ race: raceNameMap[selectedRaceLabel] })
                    }
                  }}
                >
                  <For each={props.electionOptions}>
                    {({ label, value }) => (
                      <option value={value}>{label}</option>
                    )}
                  </For>
                </select>
              </div>
            </Show>
            <div class="select">
              <select
                aria-label="Race"
                value={state.race}
                onChange={(e) => setState({ race: e.target.value })}
              >
                <For each={raceOptions()}>
                  {({ label, value }) => <option value={value}>{label}</option>}
                </For>
              </select>
            </div>
          </form>
          <Legend
            candidates={mapStore.candidates || []}
            totalVotes={mapStore.electionResults.total}
            displayOverrides={props.displayOverrides}
          />
          <Show when={UNOFFICIAL_RESULTS.includes(state.election)}>
            <p class="unofficial-notice">
              Unofficial results as of Apr. 8, 3:25pm
            </p>
          </Show>
          <Show when={props.embedAttribution}>
            <a
              class="embed-attribution"
              href="https://detroitelectionmaps.org"
              target="_blank"
              rel="noopener"
            >
              See more at Detroit Election Maps
            </a>
          </Show>
        </div>
      </div>
      <Show when={mapStore.map}>
        <Popup
          map={mapStore.map}
          layer={"precincts"}
          source={`precincts-${getPrecinctYear(state.election, +year())}`}
          active={popup.click || popup.hover}
          lngLat={popup.lngLat}
        >
          <PopupContent
            displayOverrides={props.displayOverrides}
            candidateColors={mapStore.candidateColors}
            feature={popup.feature}
          />
        </Popup>
      </Show>
    </>
  )
}

export default MapPage
