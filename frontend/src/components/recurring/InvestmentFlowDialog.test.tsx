import { render, screen } from "@testing-library/react"
import { describe, expect, it } from "vitest"
import { InvestmentFlowDialog, type FlowRecurring } from "./InvestmentFlowDialog"

const accounts = [{ id: 1, name: "PEA", currency: "EUR", type: "investissement" }]
const base: FlowRecurring = {
  name: "DCA mensuel", amount: 200, currency: "EUR", frequency: "monthly", day_of_month: 5,
  account_id: 1, ticker: "CW8.PA", isin: "FR0010315770",
}

describe("InvestmentFlowDialog", () => {
  it("affiche le nom du titre plutôt que le ticker", () => {
    render(<InvestmentFlowDialog recurring={{ ...base, security_name: "MSCI World" }} accounts={accounts} onClose={() => {}} />)
    expect(screen.getByText("MSCI World")).toBeInTheDocument()
    expect(screen.getByText("CW8.PA")).toBeInTheDocument() // ticker relégué en sous-titre
  })

  it("retombe sur le nom de la récurrence si le titre est inconnu", () => {
    render(<InvestmentFlowDialog recurring={base} accounts={accounts} onClose={() => {}} />)
    expect(screen.getAllByText("DCA mensuel").length).toBeGreaterThan(1)
  })
})
