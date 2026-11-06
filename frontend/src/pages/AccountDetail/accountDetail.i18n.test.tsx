/** Page d'un compte, crédit, transactions et virements : textes, pluriels et formats en français comme en anglais. */
import { screen, within } from "@testing-library/react"
import { http, HttpResponse } from "msw"
import { Route, Routes } from "react-router-dom"
import { setLanguage } from "@/i18n"
import { makeAccount, makeTransaction } from "@/test/factories"
import { apiUrl } from "@/test/handlers"
import { renderWithProviders } from "@/test/render"
import { server } from "@/test/server"
import { WorkTimeProvider } from "@/providers/WorkTimeProvider"
import AccountDetail from "./index"

function serveAccount() {
  server.use(
    http.get(apiUrl("/accounts/:id"), () => HttpResponse.json(makeAccount({ id: 1, name: "Compte joint", balance: 2500.5 }))),
    http.get(apiUrl("/transactions/merchants"), () => HttpResponse.json(["Carrefour"])),
    http.get(apiUrl("/analytics/asset-allocation/suggestions"), () => HttpResponse.json(null)),
    http.get(apiUrl("/transactions"), () =>
      HttpResponse.json([
        makeTransaction({ id: 7, merchant: "Carrefour", type: "Sortie", amount: 42.5, category: null }),
        makeTransaction({ id: 8, merchant: "Intérêts livret", type: "Interets", amount: 3 }),
      ])),
    http.get(apiUrl("/analytics/timeseries"), () => HttpResponse.json([])),
    http.get(apiUrl("/categories"), () => HttpResponse.json([])),
    http.get(apiUrl("/tags"), () => HttpResponse.json([])),
    http.get(apiUrl("/analytics/tags"), () => HttpResponse.json([])),
    http.get(apiUrl("/analytics/account-flow-summary"), () => HttpResponse.json(null)),
    http.get(apiUrl("/salary/work-time"), () => HttpResponse.json({ configured: false, hourly_rate: null, work_hours_per_day: 7 })),
  )
}

function renderAccount() {
  return renderWithProviders(
    <WorkTimeProvider>
      <Routes>
        <Route path="/accounts/:id" element={<AccountDetail />} />
      </Routes>
    </WorkTimeProvider>,
    { route: "/accounts/1", auth: true },
  )
}

describe("détail d'un compte", () => {
  afterEach(() => setLanguage("fr"))

  it("en français", async () => {
    serveAccount()
    renderAccount()
    expect(await screen.findByRole("heading", { name: /Compte joint/ })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /Nouvelle opération/ })).toBeInTheDocument()
    expect(screen.getByText("Flux financiers en EUR")).toBeInTheDocument()
  })

  it("en anglais : en-tête, KPI, tableau des transactions, types et montants", async () => {
    await setLanguage("en")
    serveAccount()
    const { user } = renderAccount()
    expect(await screen.findByRole("heading", { name: /Compte joint/ })).toBeInTheDocument()
    expect(screen.getByText("Cash flow in EUR")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /Reconcile/ })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /New transaction/ })).toBeInTheDocument()
    expect(screen.getByText("Current Balance")).toBeInTheDocument()
    expect(screen.getByText("Monthly Net Flow")).toBeInTheDocument()

    const table = await screen.findByRole("table")
    for (const header of ["Date", "Merchant", "Category / Type", "Amount", "Balance"]) {
      expect(within(table).getByRole("columnheader", { name: new RegExp(header) })).toBeInTheDocument()
    }
    expect(within(table).getByText("Uncategorized")).toBeInTheDocument()
    expect(within(table).getByText("Interest")).toBeInTheDocument()
    expect(within(table).getByText("-€42.50")).toBeInTheDocument()

    await user.click(screen.getByRole("button", { name: /New transaction/ }))
    const dialog = await screen.findByRole("dialog")
    expect(within(dialog).getByText("Enter the transaction details.")).toBeInTheDocument()
    expect(within(dialog).getByLabelText("Merchant / Label")).toHaveAttribute("placeholder", "E.g. Carrefour...")
    expect(within(dialog).getByRole("button", { name: "Save" })).toBeInTheDocument()
  })

  it("en anglais : sélection groupée avec pluriel", async () => {
    await setLanguage("en")
    serveAccount()
    const { user } = renderAccount()
    const table = await screen.findByRole("table")
    const checkboxes = within(table).getAllByRole("checkbox")
    await user.click(checkboxes[0])
    expect(await screen.findByText("selected")).toBeInTheDocument()
    await user.click(screen.getByRole("button", { name: "Edit" }))
    expect(await screen.findByText("Apply these changes to the 2 selected transactions.")).toBeInTheDocument()
  })
})
