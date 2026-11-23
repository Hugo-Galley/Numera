/** Sankey en liste (mobile) : une section par nœud dans l'ordre du flux, montants de l'API, catégories cliquables. */
import { render, screen, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { SankeyList } from "@/components/analytics/SankeyList"
import type { SankeyData } from "@/components/analytics/sankeyLayout"

const data: SankeyData = {
  nodes: [
    { name: "Budget" },
    { name: "Investissements", color: "#6366f1" },
    { name: "Déficit / Trésorerie", color: "#f43f5e" },
    { name: "Fixe" },
    { name: "Logement", category_id: 13 },
    { name: "Énergie", category_id: 14 },
  ],
  links: [
    { source: 0, target: 1, value: 300 },
    { source: 2, target: 0, value: 1286 },
    { source: 0, target: 3, value: 986 },
    { source: 3, target: 4, value: 890 },
    { source: 3, target: 5, value: 96 },
  ],
}

describe("SankeyList", () => {
  it("sections dans l'ordre du flux : source, puis budget, puis groupes", () => {
    render(<SankeyList data={data} />)

    const titles = screen.getAllByRole("heading").map((h) => h.textContent)
    expect(titles[0]).toMatch(/^Déficit \/ Trésorerie/)
    expect(titles[1]).toMatch(/^Budget/)
    expect(titles[2]).toMatch(/^Fixe/)
  })

  it("chaque flux sortant avec son montant, triés du plus gros au plus petit", () => {
    render(<SankeyList data={data} />)

    const budget = within(screen.getByRole("region", { name: "Budget" }))
    const rows = budget.getAllByRole("listitem").map((li) => li.textContent)
    expect(rows[0]).toMatch(/^Fixe.*986,00/)
    expect(rows[1]).toMatch(/^Investissements.*300,00/)
  })

  it("une catégorie se clique (drill-down), un groupe non", async () => {
    const onCategoryClick = vi.fn()
    render(<SankeyList data={data} onCategoryClick={onCategoryClick} />)

    await userEvent.click(screen.getByRole("button", { name: /Logement/ }))
    expect(onCategoryClick).toHaveBeenCalledWith(13, "Logement")
    expect(screen.queryByRole("button", { name: /^Fixe/ })).not.toBeInTheDocument()
  })

  it("sans réponse ou sans flux : message de chargement / d'absence de données", () => {
    const { rerender } = render(<SankeyList data={null} />)
    expect(screen.queryByRole("heading")).not.toBeInTheDocument()
    rerender(<SankeyList data={{ nodes: [], links: [] }} />)
    expect(screen.queryByRole("heading")).not.toBeInTheDocument()
  })
})
