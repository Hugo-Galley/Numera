/** Écart du bilan vs mois précédent : le pourcentage porte son signe, comme sur la page Comparaison. */
import { render, screen } from "@testing-library/react"
import { Delta } from "@/components/monthly-report/Delta"
import { formatRate } from "@/lib/utils"

describe("Delta", () => {
  it("baisse : montant et pourcentage négatifs (« −100 % », pas « 100 % »)", () => {
    render(<Delta diff={-2858.45} pct={-100} upIsBad={false} />)

    const text = screen.getByText(/2\s858,45/).textContent ?? ""
    expect(text).toContain("−")
    expect(text).toContain(`(${formatRate(-100, 0, true)})`)
    expect(text).not.toContain("(100")
  })

  it("hausse : pourcentage préfixé de « + »", () => {
    render(<Delta diff={100} pct={3} upIsBad={false} />)

    expect(screen.getByText(/100,00/).textContent).toContain(`(${formatRate(3, 0, true)})`)
  })

  it("écart négligeable : « stable »", () => {
    render(<Delta diff={0.2} pct={0} />)

    expect(screen.getByText("stable")).toBeInTheDocument()
  })

  it("pourcentage qui s'arrondit à 0 : pas de « (−0 %) »", () => {
    render(<Delta diff={-3.25} pct={-0.11} upIsBad={false} />)

    expect(screen.getByText(/3,25/).textContent).not.toContain("(")
  })
})
