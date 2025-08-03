export const DEFAULT_ELECTION = "2024-general"

export const COLOR_SCHEME = [
  "#1f77b4",
  "#d62728",
  "#2ca02c",
  "#ff7f0e",
  "#9467bd",
  "#8c564b",
  "#e377c2",
  "#7f7f7f",
  "#bcbd22",
  "#17becf",
]

// TODO: Maybe add election and/or race key into this to be safe? Could be many "Johnson"s
const COLOR_OVERRIDES = {
  turnout: "#279989",
}

export const getColor = (candidate, index) =>
  COLOR_OVERRIDES[candidate.replace(" Percent", "")] ||
  COLOR_SCHEME[index % COLOR_SCHEME.length]

export const getDataCols = (row) =>
  Object.keys(row || {}).filter(
    (row) => row.includes("Percent") || row === "turnout"
  )
