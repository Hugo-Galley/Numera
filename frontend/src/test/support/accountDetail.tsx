/** Page d'un compte servie par MSW : lectures d'un compte courant, écritures consignées sur /transactions. */
import { http, HttpResponse } from "msw"
import { Route, Routes } from "react-router-dom"
import { makeAccount } from "@/test/support/factories"
import { apiUrl } from "@/test/support/handlers"
import { renderWithProviders } from "@/test/support/render"
import { server } from "@/test/support/server"
import { WorkTimeProvider } from "@/providers/WorkTimeProvider"
import type { Account, Transaction } from "@/pages/AccountDetail/types"
import AccountDetail from "@/pages/AccountDetail/index"

export interface Backend {
  account: Account
  transactions: Transaction[]
  writes: { method: string; path: string; body: unknown }[]
  listCalls: number
}

/** Répond aux lectures de la page d'un compte courant et consigne les écritures sur /transactions. */
export function serveAccount(transactions: Transaction[] = [], account = makeAccount({ id: 1, name: "Compte joint" })): Backend {
  const backend: Backend = { account, transactions, writes: [], listCalls: 0 }
  const record = async (request: Request) => {
    const text = await request.text()
    backend.writes.push({ method: request.method, path: new URL(request.url).pathname, body: text ? JSON.parse(text) : null })
  }
  server.use(
    http.get(apiUrl("/accounts/:id"), () => HttpResponse.json(backend.account)),
    http.get(apiUrl("/transactions/merchants"), () => HttpResponse.json(["Carrefour"])),
    http.get(apiUrl("/analytics/asset-allocation/suggestions"), () => HttpResponse.json(null)),
    http.get(apiUrl("/transactions"), () => {
      backend.listCalls++
      return HttpResponse.json(backend.transactions)
    }),
    http.get(apiUrl("/analytics/timeseries"), () => HttpResponse.json([])),
    http.get(apiUrl("/categories"), () => HttpResponse.json([])),
    http.get(apiUrl("/tags"), () => HttpResponse.json([])),
    http.get(apiUrl("/analytics/tags"), () => HttpResponse.json([])),
    http.get(apiUrl("/analytics/account-flow-summary"), () => HttpResponse.json(null)),
    http.get(apiUrl("/salary/work-time"), () => HttpResponse.json({ configured: false, hourly_rate: null, work_hours_per_day: 7 })),
    http.post(apiUrl("/transactions"), async ({ request }) => {
      await record(request)
      return HttpResponse.json({ id: 99 })
    }),
    http.patch(apiUrl("/transactions/:id"), async ({ request }) => {
      await record(request)
      return HttpResponse.json({})
    }),
    http.delete(apiUrl("/transactions/:id"), async ({ request }) => {
      await record(request)
      return new HttpResponse(null, { status: 204 })
    }),
  )
  return backend
}

/** `WorkTimeProvider` : le menu d'une sortie affiche son prix en heures de travail. */
export function renderAccount(route = "/accounts/1") {
  return renderWithProviders(
    <WorkTimeProvider>
      <Routes>
        <Route path="/accounts/:id" element={<AccountDetail />} />
      </Routes>
    </WorkTimeProvider>,
    { route, auth: true },
  )
}
