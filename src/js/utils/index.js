export function setupNavToggle() {
  const navToggle = document.getElementById("nav-toggle")
  if (!navToggle) return

  navToggle.addEventListener("click", () => {
    const expanded = navToggle.getAttribute("aria-expanded")
    navToggle.setAttribute("aria-expanded", !(expanded === "true"))
  })
}

export function descending(a, b) {
  return a == null || b == null
    ? NaN
    : b < a
    ? -1
    : b > a
    ? 1
    : b >= a
    ? 0
    : NaN
}

export function formToObj(form) {
  const formObj = {}
  const formNames = [
    ...new Set(
      Object.values(form.elements)
        .map(
          (input) =>
            (input instanceof NodeList || input instanceof HTMLCollection
              ? input[0]
              : input
            ).name
        )
        .filter((name) => !!name)
    ),
  ]
  const formData = new FormData(form)

  formNames.map((name) => {
    let value = formData.getAll(name).join(",")
    if (form.elements[name].type === "checkbox") {
      value = !!value
    }
    formObj[name] = value
  })
  return formObj
}

export function formToSearchParams(form) {
  const params = new URLSearchParams({
    ...Object.fromEntries(new URLSearchParams(window.location.search)),
    ...Object.fromEntries(Object.entries(formToObj(form))),
  })
  window.history.replaceState(
    {},
    window.document.title,
    `${window.location.protocol}//${window.location.host}${
      window.location.pathname
    }${params.toString() === `` ? `` : `?${params}`}${window.location.hash}`
  )
}

export function searchParamsToForm(form) {
  const searchParams = new URLSearchParams(window.location.search)

  for (let [key, value] of searchParams.entries()) {
    if (!(key in form.elements)) return
    const input = form.elements[key]
    if (input.length > 1) {
      value = value.split(",")
      input.forEach((inputEl) => {
        inputEl.checked = value.includes(inputEl.value)
      })
    } else if (input.type === "checkbox") {
      input.checked = !!value
    } else {
      input.value = value
    }
  }
}
export const fromEntries = (entries) =>
  entries.reduce((acc, [key, value]) => ({ ...acc, [key]: value }), {})

export const objectFromSearchParams = (params) => {
  const obj = {}
  params.forEach((val, key) => {
    obj[key] = val
  })
  return obj
}

export function updateQueryParams(params) {
  // Retain query params not included in the params we're updating
  const initParams = fromEntries(
    Object.entries(
      objectFromSearchParams(new URLSearchParams(window.location.search))
    ).filter((vals) => !Object.keys(params).includes(vals[0]))
  )
  const cleanParams = fromEntries(
    Object.entries(params).filter(([key, value]) =>
      key === `page` ? value > 1 : !!value
    )
  )
  // Merge the existing, unwatched params with the filter params
  const updatedParams = new URLSearchParams({
    ...initParams,
    ...cleanParams,
  })
  const suffix = updatedParams.toString() === `` ? `` : `?${updatedParams}`
  window.history.replaceState(
    {},
    window.document.title,
    `${window.location.protocol}//${window.location.host}${window.location.pathname}${suffix}${window.location.hash}`
  )
}
