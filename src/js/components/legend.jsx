import { For } from "solid-js"

const Legend = (props) => (
  <>
    <div
      class="color-ramp"
      style={{ "background-image": "linear-gradient(to right, #fff, #333)" }}
    >
      <span class="ramp-label">0%</span>
      <span class="ramp-label">100%</span>
    </div>
    <For each={props.candidates}>
      {({ name, color, votes }) => (
        <div class="legend-row">
          <div class="legend-row-details">
            <span class="color" style={{ "background-color": color }} />{" "}
            <span class="label">{props.displayOverrides[name] || name}</span>
          </div>
          <div class="numbers">
            <div class="hidden">{votes.toLocaleString()}</div>
            <Show when={!isNaN(votes / props.totalVotes)}>
              <div class="percent">
                {((votes / props.totalVotes) * 100)
                  .toFixed(1)
                  .replace("100.0", "100")}
                %
              </div>
            </Show>
          </div>
        </div>
      )}
    </For>
  </>
)

export default Legend
