const production = process.env.NODE_ENV === "production"

const baseurl = production ? "" : ""

const host = production ? process.env.SITE_HOST || "" : "http://0.0.0.0:8080"

export default {
  name: "Detroit Election Maps",
  title: "Detroit Election Maps",
  description: "",
  type: "website",
  baseurl,
  url: `${host}${baseurl}`,
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
