/** Estimation des PRU depuis les achats saisis : lignes cochées d'office, valeurs corrigeables, enregistrement groupé. */
import { screen, waitFor } from "@testing-library/react"
import { vi } from "vitest"
import { http, HttpResponse } from "msw"
import { apiUrl } from "@/test/support/handlers"
import { renderWithProviders } from "@/test/support/render"
import { server } from "@/test/support/server"
import { CostEstimateDialog } from "@/components/investments/CostEstimateDialog"

const base = { quantity: 10, currency: "EUR", current_cost: null, estimate: 100, buys: 2, bought_quantity: 10, sold_quantity: 0, coverage: 1, first_buy: "2025-01-10", method: "quantities", amount_only_buys: 0 }
const rows = [
  { ...base, ticker: "CW8.PA", asset_name: "Amundi MSCI World" },
  { ...base, ticker: "AI.PA", asset_name: "Air Liquide", current_cost: 90, estimate: 120 },
  { ...base, ticker: "MC.PA", asset_name: "LVMH", coverage: 0.6, sold_quantity: 2, estimate: 700 },
  { ...base, ticker: "XYZ", asset_name: "Titre sans achat", estimate: null, buys: 0, coverage: null },
  { ...base, ticker: "VWCE.DE", asset_name: "Vanguard FTSE", method: "amounts", coverage: null, estimate: 95.5, amount_only_buys: 1 },
]

function setup(data: object[] = rows) {
  const applied: unknown[] = []
  server.use(
    http.get(apiUrl("/holdings/estimate-costs"), () => HttpResponse.json(data)),
    http.post(apiUrl("/holdings/apply-costs"), async ({ request }) => { applied.push(await request.json()); return HttpResponse.json({}) }),
  )
  const onOpenChange = vi.fn()
  const onApplied = vi.fn()
  const view = renderWithProviders(<CostEstimateDialog open onOpenChange={onOpenChange} accountId={5} onApplied={onApplied} />, { auth: true })
  return { applied, onOpenChange, onApplied, ...view }
}

const check = (ticker: string) => screen.getByRole("checkbox", { name: `Appliquer le PRU de ${ticker}` })

describe("CostEstimateDialog", () => {
  it("coche d'office les estimations complètes dont le PRU est vide, pas les autres", async () => {
    setup()

    expect(await screen.findByText("Amundi MSCI World")).toBeInTheDocument()
    expect(check("CW8.PA")).toBeChecked()
    expect(check("VWCE.DE")).toBeChecked() // estimation « total versé ÷ parts »
    expect(check("AI.PA")).not.toBeChecked() // PRU déjà renseigné
    expect(check("MC.PA")).not.toBeChecked() // couvre 60 % des parts seulement
    expect(check("XYZ")).not.toBeChecked() // aucun achat
    expect(screen.getByRole("button", { name: "Enregistrer 2 PRU" })).toBeEnabled()
  })

  it("signale les estimations partielles, par montants, les ventes et l'absence d'achat", async () => {
    setup()

    expect(await screen.findByText("Couvre 60 % des parts")).toBeInTheDocument()
    expect(screen.getByText("2 vendue(s)")).toBeInTheDocument()
    expect(screen.getByText("Estimé : total versé ÷ parts")).toBeInTheDocument()
    expect(screen.getByText("Aucun achat saisi : à renseigner à la main")).toBeInTheDocument()
    expect(screen.getByText(/PRU actuel 90 EUR/)).toBeInTheDocument()
  })

  it("enregistre les lignes cochées avec leur valeur, corrigée à la main si besoin", async () => {
    const { user, applied, onApplied, onOpenChange } = setup()
    await screen.findByText("Amundi MSCI World")

    await user.click(check("AI.PA"))
    const inputs = screen.getAllByPlaceholderText("PRU")
    await user.clear(inputs[0])
    await user.type(inputs[0], "98.25")
    await user.click(screen.getByRole("button", { name: /Enregistrer \d PRU/ }))

    await waitFor(() => expect(onApplied).toHaveBeenCalledTimes(1))
    expect(applied).toEqual([{ account_id: 5, items: [{ ticker: "CW8.PA", buy_price_avg: 98.25 }, { ticker: "AI.PA", buy_price_avg: 120 }, { ticker: "VWCE.DE", buy_price_avg: 95.5 }] }])
    expect(onOpenChange).toHaveBeenCalledWith(false)
    expect(await screen.findByText("3 PRU enregistrés")).toBeInTheDocument()
  })

  it("saisir une valeur coche la ligne ; la vider la décoche et désactive le bouton si plus rien", async () => {
    const { user } = setup([{ ...base, ticker: "XYZ", asset_name: "Titre sans achat", estimate: null, buys: 0, coverage: null }])
    await screen.findByText("Titre sans achat")
    expect(screen.getByRole("button", { name: "Enregistrer 0 PRU" })).toBeDisabled()

    await user.type(screen.getByPlaceholderText("PRU"), "42")
    expect(check("XYZ")).toBeChecked()
    expect(screen.getByRole("button", { name: "Enregistrer 1 PRU" })).toBeEnabled()

    await user.clear(screen.getByPlaceholderText("PRU"))
    expect(check("XYZ")).not.toBeChecked()
    expect(screen.getByRole("button", { name: "Enregistrer 0 PRU" })).toBeDisabled()
  })

  it("inventaire vide : message", async () => {
    setup([])

    expect(await screen.findByText("Aucune ligne dans l'inventaire du Point Zéro.")).toBeInTheDocument()
  })

  it("enregistrement refusé : message d'erreur, fenêtre ouverte", async () => {
    const { user, onApplied, onOpenChange } = setup()
    server.use(http.post(apiUrl("/holdings/apply-costs"), () => HttpResponse.json({ detail: "Position introuvable" }, { status: 404 })))
    await screen.findByText("Amundi MSCI World")

    await user.click(screen.getByRole("button", { name: /Enregistrer \d PRU/ }))

    expect(await screen.findByText("Position introuvable")).toBeInTheDocument()
    expect(onApplied).not.toHaveBeenCalled()
    expect(onOpenChange).not.toHaveBeenCalledWith(false)
  })

  it("estimation impossible à charger : message et fermeture", async () => {
    const onOpenChange = vi.fn()
    server.use(http.get(apiUrl("/holdings/estimate-costs"), () => HttpResponse.json({ detail: "KO" }, { status: 500 })))
    renderWithProviders(<CostEstimateDialog open onOpenChange={onOpenChange} accountId={5} onApplied={vi.fn()} />, { auth: true })

    expect(await screen.findByText("Impossible d'estimer les PRU")).toBeInTheDocument()
    await waitFor(() => expect(onOpenChange).toHaveBeenCalledWith(false))
  })
})
