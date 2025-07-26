import { For, createMemo } from "solid-js"
import { descending } from "../utils"
import { getDataCols } from "../utils/map"

const PopupContent = (props) => {
  const candidateData = createMemo(() =>
    getDataCols(props.feature || {})
      .map((c) => ({
        label: c.replace(" Percent", ""),
        value: props.feature[c],
      }))
      .sort((a, b) => descending(a.value, b.value))
  )

  return (
    <>
      <h3>Precinct {props?.feature?.id}</h3>
      <For each={candidateData()}>
        {({ label, value }) => (
          <div class="legend-row">
            <div class="legend-row-details">
              <span
                class="color"
                style={{ "background-color": props.candidateColors[label] }}
              />
              <span>{props.displayOverrides[label] || label}</span>
            </div>
            <div class="numbers">
              <div>
                {props.feature[
                  label === "turnout" ? "total" : label
                ].toLocaleString()}
              </div>
              <div class="percent">
                {value.toFixed(1).replace("100.0", "100")}%
              </div>
            </div>
          </div>
        )}
      </For>
    </>
  )
}

export default PopupContent
