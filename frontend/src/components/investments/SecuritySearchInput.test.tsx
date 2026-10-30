/** Recherche de titre : requête différée, sélection, validation du ticker / ISIN, réponses obsolètes. */
import { screen, waitFor } from "@testing-library/react"
import { http, HttpResponse } from "msw"
import { useState } from "react"
import { apiUrl } from "@/test/handlers"
import { renderWithProviders } from "@/test/render"
import { server } from "@/test/server"
import { SecuritySearchInput, type SelectedAsset } from "./SecuritySearchInput"

/** Réponse retenue jusqu'à `release()`, pour faire arriver les réponses dans le désordre. */
function held<T>(value: T) {
  let release!: () => void
  const gate = new Promise<void>((resolve) => (release = resolve))
  return { release, respond: async () => (await gate, HttpResponse.json(value as object)) }
}

const apple = { symbol: "AAPL", name: "Apple Inc.", isin: "US0378331005", type: "EQUITY", currency: "USD", price: 190, price_eur: 175.2, exchange: "NMS" }
const cw8 = { symbol: "CW8.PA", name: "Amundi MSCI World", isin: "LU1681043599", type: "ETF", currency: "EUR", price: 520, price_eur: 520, etf_profile_id: 3 }

function Harness({ onSelect, initialTicker = "" }: { onSelect?: (asset: SelectedAsset) => void; initialTicker?: string }) {
  const [ticker, setTicker] = useState(initialTicker)
  const [isin, setIsin] = useState("")
  return (
    <SecuritySearchInput
      ticker={ticker}
      isin={isin}
      onChangeTicker={setTicker}
      onChangeIsin={setIsin}
      onSelectAsset={(asset) => {
        setTicker(asset.symbol)
        onSelect?.(asset)
      }}
    />
  )
}

function recordSearches(respond: (q: string) => Response | Promise<Response>) {
  const queries: string[] = []
  server.use(
    http.get(apiUrl("/market/search"), ({ request }) => {
      const q = new URL(request.url).searchParams.get("q") ?? ""
      queries.push(q)
      return respond(q)
    }),
  )
  return queries
}

describe("SecuritySearchInput : recherche", () => {
  it("attend la fin de la frappe et n'envoie qu'une requête, rien sous deux caractères", async () => {
    const queries = recordSearches(() => HttpResponse.json([apple]))
    const { user } = renderWithProviders(<Harness />)
    const search = screen.getByLabelText(/Recherche par Titre/)

    await user.type(search, "a")
    await new Promise((resolve) => setTimeout(resolve, 350))
    expect(queries).toEqual([])

    await user.type(search, "pple")
    expect(await screen.findByText("Apple Inc.")).toBeInTheDocument()
    expect(queries).toEqual(["apple"])
  })

  it("sélectionner un résultat le transmet et vide la recherche", async () => {
    recordSearches(() => HttpResponse.json([cw8]))
    server.use(http.get(apiUrl("/market/validate"), () => HttpResponse.json({ valid: true, ...cw8 })))
    const onSelect = vi.fn()
    const { user } = renderWithProviders(<Harness onSelect={onSelect} />)

    await user.type(screen.getByLabelText(/Recherche par Titre/), "world")
    await user.click(await screen.findByText("Amundi MSCI World"))

    expect(onSelect).toHaveBeenCalledWith({
      symbol: "CW8.PA",
      name: "Amundi MSCI World",
      isin: "LU1681043599",
      type: "ETF",
      currency: "EUR",
      price: 520,
      price_eur: 520,
      etf_profile_id: 3,
    })
    expect(screen.getByLabelText(/Recherche par Titre/)).toHaveValue("")
    expect(screen.getByLabelText("Ticker / Code")).toHaveValue("CW8.PA")
  })

  // Bug suspect (SecuritySearchInput.tsx, effet de recherche) : pas de drapeau `cancelled` ; une réponse lente
  // à « micro » arrivant après celle de « microsoft » remplace la liste. Entrée : frappe « micro », pause > 280 ms
  // (requête partie, réponse retenue), puis « soft » ; « microsoft » répond [Microsoft], puis « micro » répond
  // [Micron]. Obtenu : Micron affiché. Attendu : Microsoft (réponse obsolète ignorée).
  it.todo("ignore la réponse d'une recherche précédente arrivée après la dernière")
})

describe("SecuritySearchInput : validation du ticker", () => {
  it("vérifie le ticker saisi et affiche le titre reconnu avec son cours en euros", async () => {
    const symbols: string[] = []
    server.use(
      http.get(apiUrl("/market/validate"), ({ request }) => {
        symbols.push(new URL(request.url).searchParams.get("symbol_or_isin") ?? "")
        return HttpResponse.json({ valid: true, ...apple })
      }),
    )
    const { user } = renderWithProviders(<Harness />)

    await user.type(screen.getByLabelText("Ticker / Code"), "aapl")

    expect(await screen.findByText("Reconnu")).toBeInTheDocument()
    expect(screen.getByText("Apple Inc.")).toBeInTheDocument()
    expect(screen.getByText(/Cours : 175,20/)).toBeInTheDocument()
    expect(symbols).toEqual(["AAPL"])
  })

  it("signale un titre inconnu sans bloquer la saisie manuelle", async () => {
    server.use(http.get(apiUrl("/market/validate"), () => HttpResponse.json({ detail: "introuvable" }, { status: 404 })))
    const { user } = renderWithProviders(<Harness />)

    await user.type(screen.getByLabelText("Code ISIN"), "fr0000000000")

    expect(await screen.findByText(/Actif non coté en direct/)).toBeInTheDocument()
    expect(screen.getByLabelText("Code ISIN")).toHaveValue("FR0000000000")
  })

  it("ignore la validation d'un ancien ticker arrivée après celle du nouveau", async () => {
    const slow = held({ valid: true, ...apple })
    server.use(
      http.get(apiUrl("/market/validate"), ({ request }) =>
        new URL(request.url).searchParams.get("symbol_or_isin") === "AAPL" ? slow.respond() : HttpResponse.json({ valid: true, ...cw8 }),
      ),
    )
    const { user } = renderWithProviders(<Harness initialTicker="AAPL" />)
    await waitFor(() => expect(screen.getByText(/Vérification de l'actif/)).toBeInTheDocument(), { timeout: 2000 })

    const ticker = screen.getByLabelText("Ticker / Code")
    await user.clear(ticker)
    await user.type(ticker, "CW8.PA")
    expect(await screen.findByText("Amundi MSCI World")).toBeInTheDocument()

    slow.release()
    await new Promise((resolve) => setTimeout(resolve, 50))
    expect(screen.getByText("Amundi MSCI World")).toBeInTheDocument()
    expect(screen.queryByText("Apple Inc.")).not.toBeInTheDocument()
  })
})
