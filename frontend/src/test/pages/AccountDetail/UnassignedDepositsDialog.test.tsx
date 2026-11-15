/** Pop-in « Versement à relier » : versements automatiques sans titre d'un compte titres. */
import { screen, waitFor, within } from "@testing-library/react"
import { http, HttpResponse } from "msw"
import { apiUrl } from "@/test/support/handlers"
import { renderWithProviders } from "@/test/support/render"
import { server } from "@/test/support/server"
import { UnassignedDepositsDialog } from "@/pages/AccountDetail/UnassignedDepositsDialog"

type Body = Record<string, unknown>

const deposit = (over: Body = {}) => ({
  id: 7, account_id: 3, date: "2026-10-29T00:00:00", type: "versement", amount: 400, currency: "EUR",
  note: "Virement depuis Courant", ticker: null, quantity: null, recurring_transaction_id: 23, kept_as_cash: false, ...over,
})

function serve(deposits: ReturnType<typeof deposit>[]) {
  const searches: string[] = []
  const patched: { path: string; body: Body }[] = []
  server.use(
    http.get(apiUrl("/investment-transactions"), ({ request }) => {
      searches.push(new URL(request.url).search)
      return HttpResponse.json(deposits)
    }),
    http.get(apiUrl("/recurring-transactions/"), () => HttpResponse.json([{ id: 23, name: "Alimentation PEA" }])),
    http.get(apiUrl("/market/search"), () => HttpResponse.json([{ symbol: "CW8.PA", name: "Amundi MSCI World", isin: "LU1681043599", type: "ETF", currency: "EUR", etf_profile_id: 5 }])),
    http.get(apiUrl("/market/validate"), () => HttpResponse.json({ valid: true, symbol: "CW8.PA", name: "Amundi MSCI World" })),
    http.get(apiUrl("/investment-transactions/7/security-proposal"), () =>
      HttpResponse.json({ ticker: "CW8.PA", quantity: 0.8, unit_price: 500, price_currency: "EUR", price_date: "2026-10-29" })),
    http.patch(apiUrl("/investment-transactions/:id"), async ({ request, params }) => {
      patched.push({ path: `/investment-transactions/${String(params.id)}`, body: (await request.json()) as Body })
      return HttpResponse.json(deposit())
    }),
    http.patch(apiUrl("/recurring-transactions/:id"), async ({ request, params }) => {
      patched.push({ path: `/recurring-transactions/${String(params.id)}`, body: (await request.json()) as Body })
      return HttpResponse.json({ id: 23 })
    }),
  )
  return { searches, patched }
}

describe("UnassignedDepositsDialog", () => {
  it("ne s'ouvre pas quand aucun versement n'est à relier", async () => {
    const { searches } = serve([])
    renderWithProviders(<UnassignedDepositsDialog accountId={3} onDone={() => undefined} />, { auth: true })

    await waitFor(() => expect(searches).toEqual(["?account_id=3&unassigned=true"]))
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument()
  })

  it("relie le versement au titre choisi, avec la quantité proposée, et l'applique à la récurrence", async () => {
    const { patched } = serve([deposit()])
    const onDone = vi.fn()
    const { user } = renderWithProviders(<UnassignedDepositsDialog accountId={3} onDone={onDone} />, { auth: true })

    const dialog = await screen.findByRole("dialog", { name: /Versement à relier/ })
    expect(within(dialog).getByText("Virement depuis Courant")).toBeInTheDocument()
    expect(within(dialog).getByText(/400,00/)).toBeInTheDocument()

    await user.type(within(dialog).getByLabelText(/Recherche par Titre/), "msci")
    await user.click(await within(dialog).findByText("Amundi MSCI World"))
    await waitFor(() => expect(within(dialog).getByLabelText("Quantité")).toHaveValue(0.8))
    expect(within(dialog).getByLabelText(/Prix unitaire/)).toHaveValue(500)
    expect(within(dialog).getByText(/Cours de clôture du 29\/10\/2026/)).toBeInTheDocument()

    await user.click(await within(dialog).findByRole("checkbox", { name: /prochains virements « Alimentation PEA »/ }))
    await user.click(within(dialog).getByRole("button", { name: "Relier" }))

    await waitFor(() => expect(patched).toEqual([
      { path: "/investment-transactions/7", body: { ticker: "CW8.PA", isin: "LU1681043599", quantity: 0.8, unit_price: 500, price_currency: "EUR", etf_profile_id: 5 } },
      { path: "/recurring-transactions/23", body: { ticker: "CW8.PA", isin: "LU1681043599", etf_profile_id: 5 } },
    ]))
    expect(await screen.findByText("Versement relié à CW8.PA")).toBeInTheDocument()
    expect(onDone).toHaveBeenCalledTimes(1)
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument())
  })

  it("laisse un versement en espèces puis passe au suivant", async () => {
    const { patched } = serve([deposit(), deposit({ id: 8, note: "Second versement" })])
    const { user } = renderWithProviders(<UnassignedDepositsDialog accountId={3} onDone={() => undefined} />, { auth: true })

    const dialog = await screen.findByRole("dialog", { name: /Versement à relier/ })
    expect(within(dialog).getByText("1 sur 2")).toBeInTheDocument()
    await user.click(within(dialog).getByRole("button", { name: "Laisser en espèces" }))

    await waitFor(() => expect(patched).toEqual([{ path: "/investment-transactions/7", body: { kept_as_cash: true } }]))
    expect(await within(dialog).findByText("Second versement")).toBeInTheDocument()
    expect(within(dialog).getByText("2 sur 2")).toBeInTheDocument()
  })

  it("refuse de relier sans titre ni quantité, et « Plus tard » ferme sans rien écrire", async () => {
    const { patched } = serve([deposit()])
    const { user } = renderWithProviders(<UnassignedDepositsDialog accountId={3} onDone={() => undefined} />, { auth: true })

    const dialog = await screen.findByRole("dialog", { name: /Versement à relier/ })
    await user.click(within(dialog).getByRole("button", { name: "Relier" }))
    expect(await screen.findByText("Choisissez un titre et indiquez la quantité.")).toBeInTheDocument()

    await user.click(within(dialog).getByRole("button", { name: "Plus tard" }))
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument())
    expect(patched).toEqual([])
  })
})
