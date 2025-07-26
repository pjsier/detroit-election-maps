import { onMount, onCleanup, createEffect } from "solid-js"
import { usePopup } from "../providers/popup"
import maplibregl from "maplibre-gl"

// TODO: not sure if the balance of providers and props is right here
const Popup = (props) => {
  const [popup, setPopup] = usePopup()
  let hoverId = null
  let popupObj = null

  const updateHoverState = (features) => {
    if (hoverId)
      props.map.removeFeatureState(
        { source: props.source, sourceLayer: "precincts", id: hoverId },
        "hover"
      )

    hoverId = features.length > 0 ? features[0].id : null
    if (hoverId) {
      props.map.setFeatureState(
        { source: props.source, sourceLayer: "precincts", id: hoverId },
        { hover: true }
      )
    }
  }

  const getFeatureData = (features) =>
    features.length > 0
      ? props.map.getFeatureState({
          source: props.source,
          sourceLayer: "precincts",
          id: features[0].id,
        })
      : null

  onMount(() => {
    popupObj = new maplibregl.Popup({
      closeButton: true,
      closeOnClick: false,
    })
      .setDOMContent(<div>{props.children}</div>)
      .addTo(props.map)

    const onMouseMove = (e) => {
      if (popup.click) return

      const features = props.map.queryRenderedFeatures(e.point, {
        layers: [props.layer],
      })

      props.map.getCanvas().style.cursor = features.length > 0 ? "pointer" : ""
      popupObj.setLngLat(e.lngLat)
      updateHoverState(features)
      setPopup({
        click: false,
        hover: true,
        feature: getFeatureData(features),
      })
    }

    const onMouseOut = () => {
      if (popup.click) return
      props.map.getCanvas().style.cursor = ""
      popupObj.remove()
      updateHoverState([])
      setPopup({ click: false, hover: false, feature: null })
    }

    const onMapClick = (e) => {
      if (popup.click) {
        // TODO: better handling of click outside, not just in boundaries
        props.map.getCanvas().style.cursor = ""
        popupObj.remove()
        updateHoverState([])
        setPopup({ click: false, hover: false, feature: null })
        return
      }

      const features = props.map.queryRenderedFeatures(e.point, {
        layers: [props.layer],
      })
      updateHoverState(features)
      if (features.length > 0) {
        props.map.getCanvas().style.cursor = "pointer"
        setPopup({
          click: true,
          hover: false,
          feature: getFeatureData(features),
        })
      }
    }

    // Not fully sure why this is needed, but otherwise popup will be empty
    onMouseOut()

    props.map.on("mousemove", props.layer, onMouseMove)
    props.map.on("mouseout", props.layer, onMouseOut)
    props.map.on("click", props.layer, onMapClick)

    popupObj.on("close", () => {
      setPopup({ click: false, hover: false, feature: null })
    })
  })

  onCleanup(() => popupObj.remove())

  createEffect(() => {
    if (props.active && !popup.click) popupObj.addTo(props.map)
    if (!props.active) popupObj.remove()
  })

  // TODO: currently a no-op
  createEffect(() => {
    if (props.lngLat) popupObj.setLngLat(props.lngLat)
  })

  createEffect(() => {
    if (!popup.selectedPoint) return

    const { type, lat, lon } = popup.selectedPoint
    const isPoint = ["Point Address", "Address Range"].includes(type)
    const zoom = isPoint ? 11.5 : 10

    props.map.flyTo({
      center: [lon, lat],
      zoom,
    })
    props.map.resize()

    if (isPoint) {
      props.map.once("moveend", () => {
        const features = props.map.queryRenderedFeatures(
          props.map.project([lon, lat]),
          { layers: [props.layer] }
        )
        updateHoverState(features)

        if (features.length > 0) {
          props.map.getCanvas().style.cursor = "pointer"
          popupObj.addTo(props.map)
          popupObj.setLngLat({ lng: lon, lat })
          setPopup({
            click: true,
            hover: false,
            feature: getFeatureData(features),
          })
        }
      })
    }
  })

  createEffect(() =>
    popupObj.setDOMContent(
      <div class={`popup ${popup.click ? `click` : ""}`}>{props.children}</div>
    )
  )

  return <></>
}

export default Popup
