import { render } from "solid-js/web"

import ReportPage from "./pages/report-page"
import elections from "./elections"
import { DEFAULT_ELECTION } from "./utils/map"
import { parseMapMetadata } from "./map"

const reportContainer = document.querySelector("main.report")

const params = new URLSearchParams(window.location.search)

const electionOptions = Object.entries(elections).map(
  ([value, { label, ..._ }]) => ({ value, label })
)

if (reportContainer) {
  const mapMetadata = parseMapMetadata()
  render(
    () => (
      <ReportPage
        {...mapMetadata}
        elections={elections}
        electionOptions={electionOptions}
        displayOverrides={{ turnout: "Turnout" }}
        dataDomain={"data.detroitelectionmaps.org"}
        initialElection={
          mapMetadata.embedElection ||
          params.get("election") ||
          DEFAULT_ELECTION
        }
        initialRace={params.get("race") || "turnout"}
        initialVoteType={params.get("voteType") || "total"}
        initialCity={params.get("city") || ``}
      />
    ),
    reportContainer
  )
}
