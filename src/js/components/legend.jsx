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
    <p>{JSON.stringify(props.displayCandidates)}</p>
    <fieldset>
      <For each={props.candidates}>
        {({ name, color, votes }) => (
          <div class="legend-row">
            <div class="legend-row-details">
              <label class="label">
                <span class="color" style={{ "background-color": color }} />{" "}
                <input
                  type="checkbox"
                  name="displayCandidates"
                  checked={props.displayCandidates.includes(name)}
                  onChange={(e) => props.onChange(name, e.target.checked)}
                />
                <span>{props.displayOverrides[name] || name}</span>
              </label>
            </div>
            <div class="numbers">
              <div>{votes.toLocaleString()}</div>
              <div class="percent">
                {((votes / props.totalVotes) * 100)
                  .toFixed(1)
                  .replace("100.0", "100")}
                %
              </div>
            </div>
          </div>
        )}
      </For>
    </fieldset>
  </>
)

export default Legend
