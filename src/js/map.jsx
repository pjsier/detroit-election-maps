import { render } from "solid-js/web"

import MapProvider from "./providers/map"
import PopupProvider from "./providers/popup"
import MapPage from "./pages/map-page"
import elections from "./elections"
import { DEFAULT_ELECTION } from "./utils/map"

const mapContainer = document.querySelector("main.map")

const params = new URLSearchParams(window.location.search)

const electionOptions = Object.entries(elections).map(([value, { label, ..._}]) => ({value, label}))

if (mapContainer) {
  render(
    () => (
      <MapProvider>
        <PopupProvider>
          <MapPage
            elections={elections}
            electionOptions={electionOptions}
            azureMapsKey={import.meta.env.VITE_AZURE_MAPS_KEY}
            displayOverrides={{turnout: "Turnout"}}
            dataDomain={import.meta.env.VITE_DATA_DOMAIN}
            initialElection={
              params.get("election") ||
              DEFAULT_ELECTION
            }
            initialRace={params.get("race") || "0"}
          />
        </PopupProvider>
      </MapProvider>
    ),
    mapContainer
  )
}
