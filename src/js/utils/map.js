export const DEFAULT_ELECTION = "2026-general"

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

const COLOR_OVERRIDES = {
  "2024-general": { "Kamala Harris": "#1f77b4", "Donald Trump": "#d62728", "Jill Stein": "#2ca02c", "Write-in": "#ff7f0e", "Elissa Slotkin": "#1f77b4", "Mike Rogers": "#d62728", "Douglas P. Marsh": "#2ca02c", },
  "2026-primary": { "Mohammad Alam": "#2ca02c" },
  "2026-general": { "Abdul El-Sayed": "#1f77b4", "Mike Rogers": "#d62728", "Jocelyn Benson": "#1f77b4", "John James": "#d62728" }
}

export const getColor = (candidate, election, index) => {
  if (candidate === "turnout") {
    return "#279989"
  }
  return (COLOR_OVERRIDES[election] || {})[candidate.replace(" Percent", "")] ||
    COLOR_SCHEME[index % COLOR_SCHEME.length]
}

export const getDataCols = (row) => {
  const dataCols = Object.keys(row || {}).filter((col) =>
    col.includes("Percent")
  )
  if (dataCols.length === 0) {
    return ["turnout"]
  }
  return dataCols
}
