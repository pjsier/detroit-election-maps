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
  "2024-general": {
    "Kamala Harris": "#1f77b4",
    "Donald Trump": "#d62728",
    "Jill Stein": "#2ca02c",
    "Write-in": "#ff7f0e",
    "Elissa Slotkin": "#1f77b4",
    "Mike Rogers": "#d62728",
    "Douglas P. Marsh": "#2ca02c",
  },
  "2026-primary": { "Mohammad Alam": "#2ca02c" },
  "2026-general": {
    "Abdul El-Sayed": "#1f77b4",
    "Mike Rogers": "#d62728",
    "Jocelyn Benson": "#1f77b4",
    "John James": "#d62728",
    "Garlin Gilchrist II": "#1f77b4",
    "Anthony G. Forlini": "#d62728",
    "Eli Savit": "#1f77b4",
    "Doug Lloyd": "#d62728",
    "Christina Bertrand Hines": "#1f77b4",
    "Michael Bouchard": "#d62728",
    "Jeremy Moss": "#1f77b4",
    "Ethan Baker": "#d62728",
    "Rashida Tlaib": "#1f77b4",
    "James Hooper": "#d62728",
    "Donavan McKinney": "#1f77b4",
    "T.P. Nykoriak": "#d62728",
    "Write-in": "#7f7f7f",
    "Jaime Churches": "#1f77b4",
    "Rylee Linting": "#d62728",
    "Sherry Berecz": "#1f77b4",
    "Jamie Thompson": "#d62728",
    "James DeSana": "#d62728",
    "Darian Counts": "#1f77b4",
    "Sarah Pounds": "#1f77b4",
    "Roman Gaskey": "#d62728",
    "Alex Hawkins": "#1f77b4",
    "Mark Tisdel": "#d62728",
    "Tom Turner": "#1f77b4",
    "Thomas E. Kuhn": "#d62728",
    "Kevin Hertel": "#1f77b4",
    "John Goldwater": "#d62728",
  },
}

export const getColor = (candidate, election, index) => {
  if (candidate === "turnout") {
    return "#279989"
  }
  return (
    (COLOR_OVERRIDES[election] || {})[candidate.replace(" Percent", "")] ||
    COLOR_SCHEME[index % COLOR_SCHEME.length]
  )
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
