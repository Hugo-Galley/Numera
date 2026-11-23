/** KPI du mois d'un compte courant : la période en cours est signalée comme incomplète (audit visuel). */
import { screen } from "@testing-library/react"
import { http, HttpResponse } from "msw"
import { makeTransaction } from "@/test/support/factories"
import { apiUrl } from "@/test/support/handlers"
import { server } from "@/test/support/server"
import { renderAccount, serveAccount } from "@/test/support/accountDetail"

describe("AccountKpis", () => {
  it("flux net et variation mensuelle : mention « mois en cours » sous les deux indicateurs", async () => {
    serveAccount([makeTransaction({ id: 5, merchant: "Boulangerie" })])
    server.use(http.get(apiUrl("/analytics/account-flow-summary"), () => HttpResponse.json({
      currency: "EUR", monthly_net_flow: -320, prev_monthly_net_flow: 150, monthly_variation: -303.6, avg_expense: 20,
    })))
    renderAccount()
    expect(await screen.findByText(/303,6/)).toBeInTheDocument()
    expect(screen.getAllByText("Mois en cours, pas encore terminé")).toHaveLength(2)
  })
})
