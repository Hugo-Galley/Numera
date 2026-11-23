/** Diagramme Sankey (bureau) : dessiné une fois la largeur connue, catégories cliquables, infobulle au survol. */
import { fireEvent, render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { SankeyFlow } from "@/components/analytics/SankeyFlow"
import type { SankeyData } from "@/components/analytics/sankeyLayout"

const data: SankeyData = {
  nodes: [{ name: "Salaire" }, { name: "Budget" }, { name: "Logement", category_id: 13 }, { name: "Énergie et chauffage collectif", category_id: 14 }],
  links: [
    { source: 0, target: 1, value: 2000 },
    { source: 1, target: 2, value: 900 },
    { source: 1, target: 3, value: 100 },
  ],
}

describe("SankeyFlow", () => {
  beforeEach(() => {
    vi.spyOn(HTMLElement.prototype, "clientWidth", "get").mockReturnValue(900)
  })

  it("dessine les nœuds et rend les catégories cliquables (drill-down)", async () => {
    const onCategoryClick = vi.fn()
    render(<SankeyFlow data={data} onCategoryClick={onCategoryClick} />)

    expect(screen.getAllByText("Budget").length).toBeGreaterThan(0)
    const buttons = screen.getAllByRole("button")
    expect(buttons).toHaveLength(2)
    await userEvent.click(buttons[0])
    expect(onCategoryClick).toHaveBeenCalledWith(expect.any(Number), expect.any(String))
  })

  it("survol d'un nœud et d'un flux : infobulle avec le montant", () => {
    const { container } = render(<SankeyFlow data={data} />)

    const salary = screen.getAllByText("Salaire")[0].closest("g") as Element
    fireEvent.mouseMove(salary, { clientX: 10, clientY: 10 })
    expect(screen.getAllByText(/2\s000/).length).toBeGreaterThan(0)
    fireEvent.mouseLeave(salary)
    const path = container.querySelector("path") as Element
    fireEvent.mouseMove(path, { clientX: 20, clientY: 20 })
    fireEvent.mouseLeave(path)
  })

  it("écran étroit : libellé long raccourci", () => {
    vi.spyOn(HTMLElement.prototype, "clientWidth", "get").mockReturnValue(400)
    render(<SankeyFlow data={data} />)

    expect(screen.getAllByText(/^Énergie et c…/).length).toBeGreaterThan(0)
  })

  it("sans flux : message", () => {
    render(<SankeyFlow data={{ nodes: [], links: [] }} />)

    expect(screen.getByText(/Pas assez de données/)).toBeInTheDocument()
  })
})
