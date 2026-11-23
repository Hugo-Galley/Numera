/** Pastille d'icône de catégorie : lisible dans les deux thèmes même sans couleur ni icône (audit visuel). */
import { render } from "@testing-library/react"
import { CategoryIcon } from "@/components/dashboard/CategoryIcon"

describe("CategoryIcon", () => {
  it("sans couleur : fond neutre du thème (pas d'hexadécimal inline) et icône contrastée", () => {
    const { container } = render(<CategoryIcon category={{ color: null, icon: null }} />)
    const chip = container.firstElementChild as HTMLElement
    expect(chip.style.backgroundColor).toBe("")
    expect(chip).toHaveClass("bg-slate-100")
    const svg = chip.querySelector("svg")!
    expect(svg).toHaveClass("text-slate-600")
    expect(svg).not.toHaveClass("text-white")
  })

  it("sans catégorie du tout : même repli neutre, icône par défaut", () => {
    const { container } = render(<CategoryIcon category={null} />)
    expect(container.querySelector("svg")).toBeInTheDocument()
    expect(container.firstElementChild).toHaveClass("bg-slate-100")
  })

  it("avec couleur : fond de la catégorie et icône blanche", () => {
    const { container } = render(<CategoryIcon category={{ color: "#10b981", icon: "Coffee" }} />)
    const chip = container.firstElementChild as HTMLElement
    expect(chip.style.backgroundColor).toBe("rgb(16, 185, 129)")
    expect(chip.querySelector("svg")).toHaveClass("text-white")
  })
})
