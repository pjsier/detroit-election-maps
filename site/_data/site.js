const production = process.env.NODE_ENV === "production"

const host = production
  ? "https://detroitelectionmaps.org"
  : "http://0.0.0.0:8080"

export default {
  name: "Detroit Election Maps",
  title: "Detroit Election Maps",
  description: "Explore precinct-level results for Detroit elections",
  type: "website",
  baseurl: host,
  url: host,
  domain: host.replace("https://", ""),
  dataDomain: "data.detroitelectionmaps.org",
  production,
  robots: production,
  plausibleAnalytics: !!process.env.PLAUSIBLE,
  locale: "en-US",
  azureMapsKey: process.env.VITE_AZURE_MAPS_KEY,
  precinctYears: [2024],
  electionMetadata: {
    electionOrder: [],
    displayOverrides: {
      turnout: "Turnout",
    },
  },
  nav: [
    { url: "/about/", label: "About" },
    { url: "https://detroitdata.org/", label: "Data" },
  ],
}
