import { createEffect, createMemo, onCleanup, onMount } from "solid-js"
import { useMapStore } from "../providers/map"
import { usePopup } from "../providers/popup"
import { descending, fromEntries } from "../utils"
import { getDataCols, getColor } from "../utils/map"
import { getPrecinctYear, fetchCsvData } from "../utils/data"
import maplibregl from "maplibre-gl"
import "maplibre-gl/dist/maplibre-gl.css"

const compactAttribControl = () => {
  const control = document.querySelector("details.maplibregl-ctrl-attrib")
  control.removeAttribute("open")
  control.classList.remove("mapboxgl-compact-show", "maplibregl-compact-show")
}

const filterExpression = (data) => [
  "in",
  ["get", "id"],
  ["literal", data.map(({ id }) => id)],
]

const aggregateElection = (data, election, race) => {
  const dataCols = Object.keys(data[0] || {}).filter(
    (row) =>
      row.includes("Percent") ||
      ["turnout", "registered", "ballots"].includes(row)
  )
  const candidateNames = dataCols.map((c) => c.replace(" Percent", ""))

  const aggBase = {
    total: 0,
    ...candidateNames.reduce((a, v) => ({ ...a, [v]: 0 }), {}),
  }
  const electionResults = data.reduce(
    (agg, val) =>
      Object.keys(agg).reduce((a, v) => ({ ...a, [v]: agg[v] + val[v] }), {}),
    aggBase
  )

  const candidates = candidateNames
    .filter((name) => !["ballots", "registered"].includes(name))
    .map((name, idx) => ({
      name,
      color: getColor(name, idx),
      votes: electionResults[name === "turnout" ? "total" : name],
    }))
    .sort((a, b) => descending(a.votes, b.votes))

  // TODO: simplify here, maybe pull out of candidates?
  const candidateColors = candidateNames
    .filter((name) => !["ballots", "registered"].includes(name))
    .reduce((a, v, idx) => ({ ...a, [v]: getColor(v, idx) }), {})

  // Workaround for turnout display
  if (electionResults.turnout) {
    electionResults.total = electionResults.registered
  } else if (isNaN(electionResults.total)) {
    electionResults.total = electionResults.ballots
  }
  return { candidates, candidateColors, electionResults }
}

const createPrecinctLayerDefinition = (
  data,
  election,
  race,
  year,
  maxColorScale
) => ({
  layerDefinition: {
    id: "precincts",
    source: `precincts-${getPrecinctYear(election, +year)}`,
    "source-layer": "precincts",
    type: "fill",
    filter: filterExpression(data),
    paint: {
      "fill-outline-color": [
        "case",
        ["boolean", ["feature-state", "hover"], false],
        "rgba(0,0,0,0.7)",
        "rgba(0,0,0,0)",
      ],
      "fill-color": [
        "case",
        ["==", ["feature-state", "colorValue"], null],
        "#ffffff",
        [
          "interpolate",
          ["linear"],
          ["feature-state", "colorValue"],
          0,
          "#ffffff",
          maxColorScale,
          ["feature-state", "color"],
        ],
      ],
      "fill-opacity": [
        "interpolate",
        ["linear"],
        ["zoom"],
        0,
        1.0,
        10,
        1.0,
        14,
        0.8,
      ],
    },
  },
  legendData: aggregateElection(data, election, race),
})

function processFeatureData(dataCols, feature) {
  const featureData = fromEntries(
    Object.entries(feature).filter(([col]) => dataCols.includes(col))
  )
  const featureDataEntries = [...Object.entries(featureData)]
  const featureDataValues = featureDataEntries.map(([, value]) => value)
  const colorValue = Math.max(...featureDataValues)
  const colorIndex = dataCols.indexOf(
    featureDataEntries[featureDataValues.indexOf(colorValue)][0]
  )

  return {
    feature,
    colorValue,
    color: getColor(featureDataEntries[colorIndex][0], colorIndex),
  }
}

function getMaxColorScale(values) {
  const sortedAsc = [...values].sort((a, b) => a - b)
  const index = Math.ceil(0.9 * sortedAsc.length - 1)
  // Add 10% to the 90th percentile value, but cap to 100%
  return Math.min(100, sortedAsc[index] + 10)
}

function setFeatureData(map, source, feature, colorValue, color) {
  map.setFeatureState(
    {
      source,
      sourceLayer: "precincts",
      id: feature.id,
    },
    {
      color,
      colorValue,
      ...feature,
    }
  )
}

const Map = (props) => {
  let map
  let mapRef

  const [mapStore, setMapStore] = useMapStore()
  const [, setPopup] = usePopup()

  const mapSource = createMemo(
    () => `precincts-${getPrecinctYear(props.election, props.year)}`
  )

  onMount(() => {
    map = new maplibregl.Map({
      container: mapRef,
      ...props.mapOptions,
    })
    map.touchZoomRotate.disableRotation()

    map.addControl(
      new maplibregl.AttributionControl({
        compact: props.isMobile,
      }),
      props.isMobile ? "top-left" : "bottom-right"
    )
    // Workaround for a bug in maplibre-gl where the attrib is default open
    if (props.isMobile) {
      compactAttribControl()
      const timeouts = [250, 500, 1000]
      timeouts.forEach((timeout) => {
        window.setTimeout(compactAttribControl, timeout)
      })
    }
    map.once("styledata", () => {
      map.addControl(new maplibregl.NavigationControl({ showCompass: false }))
      map.addControl(new maplibregl.FullscreenControl({ container: mapRef }))
      map.resize()
    })

    setMapStore({ map })
  })

  // Based on solidjs/solid/issues/670#issuecomment-930346644
  // eslint-disable-next-line solid/reactivity
  createEffect(async () => {
    let canceled = false
    onCleanup(() => (canceled = true))
    const data = await fetchCsvData(
      props.dataDomain,
      props.election,
      props.race
    )
    if (canceled) return

    let dataCols = getDataCols(data[0] || [])
    const featureData = data.map((feature) =>
      processFeatureData(dataCols, feature)
    )
    const maxColorScale = getMaxColorScale(
      featureData.map(({ colorValue }) => colorValue)
    )

    const def = createPrecinctLayerDefinition(
      data,
      props.election,
      props.race,
      props.year,
      maxColorScale
    )
    setMapStore({ ...def.legendData })
    // Close popup on layer change
    setPopup({ click: false, hover: false })

    const updateLayer = () => {
      mapStore.map.removeLayer("precincts")
      mapStore.map.removeFeatureState({
        source: mapSource(),
        sourceLayer: "precincts",
      })
      featureData.forEach(({ feature, colorValue, color }) => {
        setFeatureData(map, mapSource(), feature, colorValue, color)
      })
      mapStore.map.addLayer(def.layerDefinition, "place_other")
    }

    if (mapStore.map.isStyleLoaded()) {
      updateLayer()
    } else {
      mapStore.map.once("render", updateLayer)
    }
  })

  onCleanup(() => {
    map.remove()
  })

  return <div id="map" ref={mapRef} />
}

export default Map
