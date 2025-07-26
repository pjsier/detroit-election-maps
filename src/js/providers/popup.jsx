import { createContext, useContext } from "solid-js"
import { createStore } from "solid-js/store"

const PopupContext = createContext()
const usePopup = () => useContext(PopupContext)

function PopupProvider(props) {
  // eslint-disable-next-line solid/reactivity
  const store = createStore({
    hover: false,
    click: false,
    lngLat: null,
    feature: null,
    selectedPoint: null,
  })

  return (
    <PopupContext.Provider value={store}>
      {props.children}
    </PopupContext.Provider>
  )
}

export { PopupProvider as default, usePopup }
