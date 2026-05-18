import { createContext, useContext } from "solid-js"
import { createStore } from "solid-js/store"

const MapContext = createContext()
const useMapStore = () => useContext(MapContext)

function MapProvider(props) {
  // eslint-disable-next-line solid/reactivity
  const store = createStore({
    map: null,
    candidates: [],
    precinctBoardMap: {},
    boardPrecinctMap: {},
  })

  return (
    <MapContext.Provider value={store}>{props.children}</MapContext.Provider>
  )
}

export { MapProvider as default, useMapStore }
