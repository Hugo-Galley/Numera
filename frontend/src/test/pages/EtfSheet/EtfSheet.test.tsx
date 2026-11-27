/** Fiche ETF : identité, pays et secteurs, liste de toutes les sociétés (recherche, tri, chargement progressif). */
import { screen, within } from "@testing-library/react"
import { http, HttpResponse } from "msw"
import { Route, Routes } from "react-router-dom"
import EtfSheetPage from "@/pages/EtfSheet"
import { apiUrl } from "@/test/support/handlers/apiUrl"
import { renderWithProviders } from "@/test/support/render"
import { server } from "@/test/support/server"
import { makeEtfSheet, makeSheetLine } from "@/test/support/etfSheet"

function serve(sheet = makeEtfSheet()) {
  server.use(http.get(apiUrl("/etf-profiles/1/constituents"), () => HttpResponse.json(sheet)))
}

const render = () =>
  renderWithProviders(<Routes><Route path="/investments/etf/:profileId" element={<EtfSheetPage />} /></Routes>, {
    route: "/investments/etf/1",
    auth: true,
  })

/** Noms de société des lignes rendues, dans l'ordre. */
const companies = () =>
  within(screen.getByRole("table")).getAllByRole("row").slice(1).map((row) => within(row).getAllByRole("cell")[0].textContent)

describe("Fiche ETF", () => {
  it("affiche le nom du fonds, son identité, la valeur détenue et un retour vers les investissements", async () => {
    serve()
    render()

    expect(await screen.findByRole("heading", { level: 1, name: "iShares Core MSCI World" })).toBeInTheDocument()
    expect(screen.getByText("IE00B4L5Y983")).toBeInTheDocument()
    expect(screen.getByText("EUNL.DE")).toBeInTheDocument()
    expect(screen.getByText("iShares · composition au 25/11/2026")).toBeInTheDocument()
    expect(screen.getByText("Physique")).toBeInTheDocument()
    expect(screen.getByText("MSCI World")).toBeInTheDocument()
    expect(screen.getByText(/3 lignes · 99,8.% du fonds/)).toBeInTheDocument()
    expect(screen.getByText(/Tu y détiens/).textContent).toMatch(/2.000,00/)
    expect(screen.getByRole("link", { name: "Investissements" })).toHaveAttribute("href", "/investments")
  })

  it("montre les pays par leur nom et les secteurs, en % du fonds", async () => {
    serve()
    render()

    const countries = await screen.findByRole("region", { name: "Pays" })
    expect(within(countries).getByText("États-Unis")).toBeInTheDocument()
    expect(within(countries).getByText(/70,0/)).toBeInTheDocument()
    expect(within(screen.getByRole("region", { name: "Secteurs" })).getByText("Technologie")).toBeInTheDocument()
  })

  it("donne pour chaque société son poids et mon exposition en euros", async () => {
    serve()
    render()

    const apple = within(await screen.findByRole("table")).getByRole("row", { name: /Apple/ })
    expect(apple).toHaveTextContent("États-Unis")
    expect(apple).toHaveTextContent(/5,00.%/)
    expect(apple).toHaveTextContent(/100,00.€/) // 5 % de 2 000 €
  })

  it("n'affiche que 50 lignes sur 120, puis 50 de plus à la demande", async () => {
    const lines = Array.from({ length: 120 }, (_, i) => makeSheetLine({ name: `Société ${i}`, weight: 1 - i / 1000 }))
    serve(makeEtfSheet({ lines, lines_count: 120 }))
    const { user } = render()

    await screen.findByRole("table")
    expect(companies()).toHaveLength(50)
    await user.click(screen.getByRole("button", { name: "Afficher 50 de plus" }))
    expect(companies()).toHaveLength(100)
    await user.click(screen.getByRole("button", { name: "Afficher 20 de plus" }))
    expect(companies()).toHaveLength(120)
    expect(screen.queryByRole("button", { name: /de plus/ })).not.toBeInTheDocument()
  })

  it("compte des lignes (pas seulement des sociétés), sans que le mode confidentialité les prenne pour un montant", async () => {
    const lines = Array.from({ length: 1501 }, (_, i) => makeSheetLine({ name: `Société ${i}`, weight: 0.05 }))
    serve(makeEtfSheet({ lines, lines_count: 1501 }))
    render()

    const title = await screen.findByText(/^1\s501 lignes$/)
    expect(title.closest("[data-privacy-ignore]")).not.toBeNull()
    expect(screen.getByText(/1\s501 lignes · /).closest("[data-privacy-ignore]")).not.toBeNull()
  })

  it("recherche par nom, ticker ou ISIN dans toute la liste", async () => {
    serve()
    const { user } = render()
    const search = await screen.findByRole("textbox", { name: "Rechercher une société" })

    for (const query of ["apple", "aapl", "us0378331005"]) {
      await user.clear(search)
      await user.type(search, query)
      expect(companies()).toHaveLength(1)
      expect(companies()[0]).toContain("Apple")
    }
    await user.clear(search)
    await user.type(search, "introuvable")
    expect(screen.getByText("Aucune société ne correspond à ta recherche.")).toBeInTheDocument()
  })

  it("trie par poids par défaut, puis par pays ou par société", async () => {
    serve()
    const { user } = render()
    await screen.findByRole("table")
    const names = () => companies().map((c) => c?.match(/Apple|Nestlé|Sony/)?.[0])
    expect(names()).toEqual(["Apple", "Sony", "Nestlé"])

    await user.click(screen.getByRole("button", { name: "Pays" })) // États-Unis, Japon, Suisse
    expect(names()).toEqual(["Apple", "Sony", "Nestlé"])
    await user.click(screen.getByRole("button", { name: "Société" }))
    expect(names()).toEqual(["Apple", "Nestlé", "Sony"])
    expect(screen.getByRole("columnheader", { name: "Société" })).toHaveAttribute("aria-sort", "ascending")
  })

  it("annonce l'ETF de référence d'un synthétique", async () => {
    const base = makeEtfSheet()
    serve(makeEtfSheet({
      profile: { ...base.profile, replication: "synthetic" }, exposure_profile_id: 2, exposure_profile_name: "Réplique physique",
    }))
    render()

    expect(await screen.findByText("Exposition de l'indice MSCI World via Réplique physique")).toBeInTheDocument()
  })

  it("sans liste complète : le dit et montre les principales lignes connues", async () => {
    serve(makeEtfSheet({
      lines: [], has_full_list: false, lines_count: 0, countries: [], provider: "yahoo", composition_as_of: null,
      top_holdings: [{ name: "NVIDIA", ticker: "NVDA", weight: 6 }],
    }))
    render()

    expect(await screen.findByText(/Cet émetteur ne publie pas la liste complète/)).toBeInTheDocument()
    expect(screen.getByText("Source : Yahoo")).toBeInTheDocument()
    expect(companies()[0]).toContain("NVIDIA")
    expect(screen.queryByRole("region", { name: "Pays" })).not.toBeInTheDocument()
  })

  it("fonds sans aucune composition : le dit franchement, sans tableau vide", async () => {
    serve(makeEtfSheet({
      lines: [], has_full_list: false, lines_count: 0, countries: [], sectors: [], top_holdings: [], provider: null,
      composition_as_of: null, coverage_pct: 0, held_value_eur: 0,
    }))
    render()

    expect(await screen.findByText("Aucune composition n'est connue pour ce fonds pour le moment.")).toBeInTheDocument()
    expect(screen.queryByRole("table")).not.toBeInTheDocument()
    expect(screen.queryByText(/Tu y détiens/)).not.toBeInTheDocument()
    expect(screen.queryByText(/liste complète/)).not.toBeInTheDocument()
  })

  it("synthétique sans référence connue : répartition indisponible", async () => {
    const base = makeEtfSheet()
    serve(makeEtfSheet({
      profile: { ...base.profile, replication: "synthetic", composition_sources: {} },
      lines: [], has_full_list: false, countries: [], sectors: [], top_holdings: [], coverage_pct: 0,
    }))
    render()

    expect(await screen.findByText("Synthétique : indice non reconnu, répartition indisponible")).toBeInTheDocument()
  })

  it("erreur de l'API : état d'erreur, et « Réessayer » relit la fiche", async () => {
    let calls = 0
    server.use(http.get(apiUrl("/etf-profiles/1/constituents"), () => {
      calls += 1
      return calls === 1 ? HttpResponse.json({ detail: "Panne" }, { status: 500 }) : HttpResponse.json(makeEtfSheet())
    }))
    const { user } = render()

    await user.click(await screen.findByRole("button", { name: "Réessayer" }))
    expect(await screen.findByRole("heading", { level: 1, name: "iShares Core MSCI World" })).toBeInTheDocument()
  })
})
