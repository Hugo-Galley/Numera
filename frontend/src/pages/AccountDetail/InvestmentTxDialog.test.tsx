/** Opération d'un compte d'investissement (dialogue « Versement / Retrait ») : validation, calcul parts × cours, envoi, erreurs. */
import { fireEvent, screen, waitFor, within } from "@testing-library/react"
import { http, HttpResponse } from "msw"
import { Route, Routes } from "react-router-dom"
import { makeAccount } from "@/test/factories"
import { apiUrl } from "@/test/handlers"
import { renderWithProviders } from "@/test/render"
import { server } from "@/test/server"
import { WorkTimeProvider } from "@/providers/WorkTimeProvider"
import AccountDetail from "./index"

type Body = Record<string, unknown>

/** Compte titres n° 5 sans opération ; `onPost` répond au `POST /investment-transactions`. */
function setup(onPost: (body: Body) => Response | Promise<Response> = () => HttpResponse.json({ id: 1 })) {
  const posted: Body[] = []
  let investmentLoads = 0
  server.use(
    http.get(apiUrl("/accounts/5"), () => HttpResponse.json(makeAccount({ id: 5, name: "PEA Boursorama", type: "investissement" }))),
    http.get(apiUrl("/accounts"), () => HttpResponse.json([])),
    http.get(apiUrl("/transactions/merchants"), () => HttpResponse.json([])),
    http.get(apiUrl("/analytics/asset-allocation/suggestions"), () => HttpResponse.json(null)),
    http.get(apiUrl("/analytics/investments/5"), () => {
      investmentLoads++
      return HttpResponse.json({ totals: {}, transactions: [], value_series: [] })
    }),
    http.get(apiUrl("/analytics/investments/5/performance-history"), () => HttpResponse.json({ items: [] })),
    http.get(apiUrl("/holdings"), () => HttpResponse.json([])),
    http.get(apiUrl("/analytics/portfolio/5"), () => HttpResponse.json(null)),
    http.get(apiUrl("/analytics/dividends"), () => HttpResponse.json(null)),
    http.get(apiUrl("/analytics/account-flow-summary"), () => HttpResponse.json(null)),
    http.get(apiUrl("/salary/work-time"), () => HttpResponse.json({ configured: false, hourly_rate: null, work_hours_per_day: 7 })),
    http.get(apiUrl("/market/validate"), () => HttpResponse.json({ valid: true, symbol: "CW8.PA", name: "Amundi MSCI World", price_eur: 520 })),
    http.post(apiUrl("/investment-transactions"), async ({ request }) => {
      const body = (await request.json()) as Body
      posted.push(body)
      return onPost(body)
    }),
  )
  const view = renderWithProviders(
    <WorkTimeProvider>
      <Routes>
        <Route path="/accounts/:id" element={<AccountDetail />} />
      </Routes>
    </WorkTimeProvider>,
    { route: "/accounts/5", auth: true },
  )
  return { ...view, posted, investmentLoads: () => investmentLoads }
}

async function openDialog(user: ReturnType<typeof setup>["user"]) {
  await user.click(await screen.findByRole("button", { name: "Versement / Retrait" }))
  return screen.getByRole("dialog", { name: "Flux d'investissement" })
}

async function chooseType(user: ReturnType<typeof setup>["user"], dialog: HTMLElement, label: string) {
  await user.click(within(dialog).getAllByRole("combobox")[0])
  await user.click(await screen.findByRole("option", { name: label }))
}

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["Date"] })
  vi.setSystemTime(new Date("2026-06-15T10:00:00"))
})
afterEach(() => vi.useRealTimers())

describe("Opération d'investissement", () => {
  it("exige un montant ou des parts", async () => {
    const { user, posted } = setup()
    const dialog = await openDialog(user)

    await user.click(within(dialog).getByRole("button", { name: "Confirmer" }))

    expect(await screen.findByText("Veuillez saisir un montant ou un nombre de parts")).toBeInTheDocument()
    expect(posted).toHaveLength(0)
  })

  it("refuse un dividende sans titre", async () => {
    const { user, posted } = setup()
    const dialog = await openDialog(user)

    await chooseType(user, dialog, "Dividende (Gain)")
    await user.type(within(dialog).getByLabelText("Montant"), "12.40")
    await user.click(within(dialog).getByRole("button", { name: "Confirmer" }))

    expect(await screen.findByText("Un dividende doit être rattaché à un titre")).toBeInTheDocument()
    expect(posted).toHaveLength(0)
  })

  it("achat : montant = parts × cours, frais, ticker en majuscules, date naïve, puis rechargement", async () => {
    const { user, posted, investmentLoads } = setup()
    const dialog = await openDialog(user)
    await waitFor(() => expect(investmentLoads()).toBe(1))

    await chooseType(user, dialog, "Achat de titres")
    fireEvent.change(dialog.querySelector('input[type="datetime-local"]')!, { target: { value: "2026-06-20T23:30" } })
    await user.type(within(dialog).getByLabelText("Ticker / Code"), "cw8.pa")
    await user.type(within(dialog).getByPlaceholderText("Ex: 2"), "2")
    await user.type(within(dialog).getByPlaceholderText("Cours..."), "520.5")
    expect(within(dialog).getByLabelText("Montant")).toHaveValue(1041)
    await user.type(within(dialog).getAllByPlaceholderText("0.00")[1], "1.5")
    await user.click(within(dialog).getByRole("button", { name: "Confirmer" }))

    expect(await screen.findByText("Opération enregistrée")).toBeInTheDocument()
    expect(posted).toEqual([
      {
        account_id: 5,
        date: "2026-06-20T23:30:00",
        type: "achat",
        amount: 1041,
        currency: "EUR",
        note: null,
        ticker: "CW8.PA",
        isin: null,
        quantity: 2,
        unit_price: 520.5,
        price_currency: "EUR",
        fees: 1.5,
        withholding_tax: null,
        reinvested: false,
        asset_class: null,
        sector: null,
        geographic_zone: null,
      },
    ])
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument())
    await waitFor(() => expect(investmentLoads()).toBe(2))
  })

  it("dividende réinvesti : retenue à la source et parts reçues obligatoires", async () => {
    const { user, posted } = setup()
    const dialog = await openDialog(user)

    await chooseType(user, dialog, "Dividende (Gain)")
    await user.type(within(dialog).getByLabelText("Montant"), "30")
    await user.type(within(dialog).getByLabelText("Ticker / Code"), "CW8.PA")
    await user.type(within(dialog).getAllByPlaceholderText("0.00")[1], "4.5")
    await user.click(within(dialog).getByRole("checkbox", { name: /Dividende réinvesti/ }))
    await user.click(within(dialog).getByRole("button", { name: "Confirmer" }))
    expect(await screen.findByText("Indique le nombre de parts reçues pour un dividende réinvesti")).toBeInTheDocument()
    expect(posted).toHaveLength(0)

    await user.type(within(dialog).getByPlaceholderText("Ex: 2"), "0.05")
    await user.click(within(dialog).getByRole("button", { name: "Confirmer" }))

    await screen.findByText("Opération enregistrée")
    expect(posted[0]).toMatchObject({ type: "dividende", amount: 30, withholding_tax: 4.5, reinvested: true, quantity: 0.05, unit_price: null, fees: null })
  })

  it("désactive « Confirmer » pendant l'envoi", async () => {
    let release!: () => void
    const gate = new Promise<void>((resolve) => (release = resolve))
    const { user, posted } = setup(async () => {
      await gate
      return HttpResponse.json({ id: 1 })
    })
    const dialog = await openDialog(user)

    await user.type(within(dialog).getByLabelText("Montant"), "500")
    await user.click(within(dialog).getByRole("button", { name: "Confirmer" }))

    const busy = await within(dialog).findByRole("button", { name: "Enregistrement…" })
    expect(busy).toBeDisabled()
    await user.click(busy)
    release()
    await screen.findByText("Opération enregistrée")
    expect(posted).toHaveLength(1)
    expect(posted[0]).toMatchObject({ type: "versement", amount: 500, date: "2026-06-15T10:00:00" })
  })

  it("affiche l'erreur du serveur et garde le dialogue ouvert", async () => {
    const { user } = setup(() => HttpResponse.json({ detail: "Solde espèces insuffisant" }, { status: 400 }))
    const dialog = await openDialog(user)

    await user.type(within(dialog).getByLabelText("Montant"), "500")
    await user.click(within(dialog).getByRole("button", { name: "Confirmer" }))

    expect(await screen.findByText("Solde espèces insuffisant")).toBeInTheDocument()
    expect(screen.getByRole("dialog", { name: "Flux d'investissement" })).toBeInTheDocument()
  })
})
