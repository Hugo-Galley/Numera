/** Point Zéro : positions existantes ou suggérées, recherche d'un titre, parts saisies, enregistrement de l'état des lieux. */
import { screen, waitFor, within } from "@testing-library/react"
import { vi } from "vitest"
import { http, HttpResponse } from "msw"
import { apiUrl } from "@/test/support/handlers"
import { renderWithProviders } from "@/test/support/render"
import { server } from "@/test/support/server"
import { PointZeroModal } from "@/components/investments/PointZeroModal"

const existing = [
  { ticker: "CW8.PA", asset_name: "Amundi MSCI World", isin: "LU1681043599", quantity: 10, buy_price_avg: 400, currency: "EUR", etf_profile_id: 4, is_etf: true, current_price: 500, current_price_eur: 500 },
]
const suggestions = [{ ticker: "AI.PA", name: "Air Liquide", isin: "FR0000120073", etf_profile_id: null, is_etf: false }]

interface Served { baselines: unknown[]; searches: string[]; decomposed: unknown[] }

/** Compte avec ou sans position ; cours et recherche de titres servis en mémoire. */
function serve({ holdings = existing as object[], suggested = suggestions as object[], search = [] as object[] } = {}): Served {
  const served: Served = { baselines: [], searches: [], decomposed: [] }
  server.use(
    http.get(apiUrl("/holdings"), () => HttpResponse.json(holdings)),
    http.get(apiUrl("/holdings/suggestions"), () => HttpResponse.json(suggested)),
    http.get(apiUrl("/market/quote"), ({ request }) => {
      const symbols = (new URL(request.url).searchParams.get("symbols") ?? "").split(",")
      return HttpResponse.json(Object.fromEntries(symbols.map((s) => [s.toUpperCase(), { price: 150, price_eur: 150, currency: "EUR" }])))
    }),
    http.get(apiUrl("/market/search"), ({ request }) => {
      served.searches.push(new URL(request.url).searchParams.get("q") ?? "")
      return HttpResponse.json(search)
    }),
    http.post(apiUrl("/etf-profiles/auto-decompose"), async ({ request }) => {
      served.decomposed.push(await request.json())
      return HttpResponse.json({ id: 77, name: "Lyxor Nasdaq", ticker: "LNQ.PA" })
    }),
    http.post(apiUrl("/holdings/baseline"), async ({ request }) => {
      served.baselines.push(await request.json())
      return HttpResponse.json({})
    }),
  )
  return served
}

function setup() {
  const onOpenChange = vi.fn()
  const onBaselineSaved = vi.fn()
  const view = renderWithProviders(
    <PointZeroModal open onOpenChange={onOpenChange} accountId={5} accountName="PEA" onBaselineSaved={onBaselineSaved} />,
    { auth: true },
  )
  return { onOpenChange, onBaselineSaved, ...view }
}

/** Champs « parts » : une saisie mobile et une saisie bureau par ligne. */
const quantityInputs = () => screen.getAllByPlaceholderText("0") as HTMLInputElement[]
/** Valeur totale du pied de fenêtre (les lignes affichent aussi leur propre valeur, en double mobile/bureau). */
const total = () => screen.getByText("Valeur totale estimée :").nextElementSibling
const searchBox = () => screen.getByPlaceholderText("ISIN, ticker (CW8.PA) ou nom…")

describe("PointZeroModal : chargement", () => {
  it("compte avec positions : lignes préremplies et valeur totale estimée", async () => {
    serve()
    setup()

    expect(screen.getByRole("dialog")).toHaveTextContent("Point Zéro : PEA")
    expect((await screen.findAllByText("Amundi MSCI World")).length).toBeGreaterThan(0)
    expect(quantityInputs()[0]).toHaveValue(10)
    // 10 parts × 500 €
    expect(total()).toHaveTextContent(/5\s000,00\s€/)
  })

  it("compte sans position : propose les titres suggérés, à 0 part, marqués « Suggéré »", async () => {
    serve({ holdings: [] })
    setup()

    expect((await screen.findAllByText("Air Liquide")).length).toBeGreaterThan(0)
    expect(screen.getAllByText("Suggéré").length).toBeGreaterThan(0)
    expect(quantityInputs()[0]).toHaveValue(null)
  })

  it("ni position ni suggestion : état vide", async () => {
    serve({ holdings: [], suggested: [] })
    setup()

    expect(await screen.findByText("Aucun actif dans cet état des lieux.")).toBeInTheDocument()
  })
})

describe("PointZeroModal : lignes", () => {
  it("saisir des parts met à jour la valeur estimée ; retirer une ligne la supprime", async () => {
    serve()
    const { user } = setup()
    await screen.findAllByText("Amundi MSCI World")

    await user.clear(quantityInputs()[1])
    await user.type(quantityInputs()[1], "2")
    expect(total()).toHaveTextContent(/1\s000,00\s€/)

    await user.click(screen.getAllByRole("button", { name: "Supprimer" })[0])
    expect(await screen.findByText("Aucun actif dans cet état des lieux.")).toBeInTheDocument()
  })
})

describe("PointZeroModal : recherche d'un titre", () => {
  const result = { symbol: "AAPL", name: "Apple Inc.", isin: "US0378331005", type: "EQUITY", currency: "USD", exchange: "NASDAQ" }

  it("moins de deux caractères : aucune recherche ; sinon résultats après un court délai", async () => {
    const served = serve({ search: [result] })
    const { user } = setup()
    await screen.findAllByText("Amundi MSCI World")

    await user.type(searchBox(), "a")
    expect(served.searches).toEqual([])
    await user.type(searchBox(), "app")

    expect(await screen.findByText("Apple Inc.")).toBeInTheDocument()
    // Seule la saisie complète est interrogée (anti-rebond), jamais « a » seul
    expect(served.searches).toEqual(["aapp"])
  })

  it("choisir un résultat : ajoute une ligne à 1 part avec son cours", async () => {
    serve({ search: [result] })
    const { user } = setup()
    await screen.findAllByText("Amundi MSCI World")

    await user.type(searchBox(), "apple")
    await user.click(await screen.findByText("Apple Inc."))

    await waitFor(() => expect(screen.getAllByText("Apple Inc.").length).toBeGreaterThan(0))
    expect(quantityInputs()).toHaveLength(4)
    expect(quantityInputs()[3]).toHaveValue(1)
    expect(searchBox()).toHaveValue("")
  })

  it("titre déjà dans la liste : message, pas de doublon", async () => {
    serve({ search: [{ ...result, symbol: "cw8.pa", name: "Amundi MSCI World" }] })
    const { user } = setup()
    await screen.findAllByText("Amundi MSCI World")

    await user.type(searchBox(), "amundi")
    await user.click(await screen.findByText("cw8.pa"))

    expect(await screen.findByText("cw8.pa est déjà dans votre liste")).toBeInTheDocument()
    expect(quantityInputs()).toHaveLength(2)
  })

  it("ETF sans profil connu : décomposition automatique, profil rattaché à la ligne", async () => {
    const served = serve({ search: [{ symbol: "LNQ.PA", name: "Lyxor Nasdaq", type: "ETF", currency: "EUR" }] })
    const { user } = setup()
    await screen.findAllByText("Amundi MSCI World")

    await user.type(searchBox(), "nasdaq")
    await user.click(await screen.findByText("Lyxor Nasdaq"))

    await waitFor(() => expect(served.decomposed).toEqual([{ symbol: "LNQ.PA", name: "Lyxor Nasdaq" }]))
    expect(await screen.findByText("Lyxor Nasdaq décomposé avec succès !")).toBeInTheDocument()
  })

  it("aucun résultat : propose de définir un ETF personnalisé, qui ouvre la fenêtre dédiée", async () => {
    serve({ search: [] })
    const { user } = setup()
    await screen.findAllByText("Amundi MSCI World")

    await user.type(searchBox(), "zzz")
    await user.click(await screen.findByRole("button", { name: "Définir cet ETF personnalisé" }))

    const dialog = await screen.findByRole("dialog", { name: "Définir un profil d'ETF" })
    expect(within(dialog).getByLabelText("Ticker / Symbole")).toBeInTheDocument()
  })

  it("« Effacer la recherche » vide le champ", async () => {
    serve({ search: [result] })
    const { user } = setup()
    await screen.findAllByText("Amundi MSCI World")
    await user.type(searchBox(), "apple")

    await user.click(screen.getByRole("button", { name: "Effacer la recherche" }))

    expect(searchBox()).toHaveValue("")
  })
})

describe("PointZeroModal : enregistrement", () => {
  it("POST du compte et des lignes à parts > 0, puis callback et fermeture", async () => {
    const served = serve({ holdings: [...existing, { ...existing[0], ticker: "VWCE.DE", asset_name: "Vanguard FTSE", quantity: 0, etf_profile_id: null }] })
    const { user, onBaselineSaved, onOpenChange } = setup()
    await screen.findAllByText("Amundi MSCI World")

    await user.click(screen.getByRole("button", { name: "Enregistrer l'état des lieux" }))

    await waitFor(() => expect(onBaselineSaved).toHaveBeenCalledTimes(1))
    expect(served.baselines).toEqual([
      { account_id: 5, holdings: [{ ticker: "CW8.PA", asset_name: "Amundi MSCI World", isin: "LU1681043599", quantity: 10, buy_price_avg: 400, currency: "EUR", etf_profile_id: 4 }] },
    ])
    expect(onOpenChange).toHaveBeenCalledWith(false)
    expect(await screen.findByText("État des lieux enregistré avec succès")).toBeInTheDocument()
  })

  it("aucune ligne à parts > 0 : message, aucune requête", async () => {
    const served = serve({ holdings: [], suggested: suggestions })
    const { user, onBaselineSaved } = setup()
    await screen.findAllByText("Air Liquide")

    await user.click(screen.getByRole("button", { name: "Enregistrer l'état des lieux" }))

    expect(await screen.findByText(/Veuillez renseigner un nombre de parts/)).toBeInTheDocument()
    expect(served.baselines).toEqual([])
    expect(onBaselineSaved).not.toHaveBeenCalled()
  })

  it("échec serveur : message d'erreur, fenêtre ouverte", async () => {
    serve()
    server.use(http.post(apiUrl("/holdings/baseline"), () => HttpResponse.json({ detail: "Compte verrouillé" }, { status: 400 })))
    const { user, onBaselineSaved, onOpenChange } = setup()
    await screen.findAllByText("Amundi MSCI World")

    await user.click(screen.getByRole("button", { name: "Enregistrer l'état des lieux" }))

    expect(await screen.findByText("Compte verrouillé")).toBeInTheDocument()
    expect(onBaselineSaved).not.toHaveBeenCalled()
    expect(onOpenChange).not.toHaveBeenCalled()
  })

  it("« Annuler » ferme sans rien envoyer", async () => {
    const served = serve()
    const { user, onOpenChange } = setup()
    await screen.findAllByText("Amundi MSCI World")

    await user.click(screen.getByRole("button", { name: "Annuler" }))

    expect(onOpenChange).toHaveBeenCalledWith(false)
    expect(served.baselines).toEqual([])
  })
})
