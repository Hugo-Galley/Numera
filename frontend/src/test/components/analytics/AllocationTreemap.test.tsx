/** Treemap d'allocation : la part « Non classé » est neutre (le rouge signifie une perte). */
import { render } from "@testing-library/react"
import { TreemapCell } from "@/components/analytics/AllocationTreemap"
import { CATEGORY_COLORS, NEUTRAL_COLOR } from "@/lib/chartPalette"

const cell = (name: string, index: number) => {
  const { container } = render(
    <svg><TreemapCell x={0} y={0} width={200} height={120} index={index} name={name} value={1000} percentage={99.34} depth={2} /></svg>,
  )
  return container
}

describe("AllocationTreemap : cases", () => {
  it("colore « Non classé » en gris neutre, même en première position", () => {
    expect(cell("Non classé", 0).querySelector("rect")?.style.fill).toBe(hexToRgb(NEUTRAL_COLOR))
  })

  it("colore une classe d'actif avec la palette, jamais en rouge", () => {
    expect(cell("Actions", 0).querySelector("rect")?.style.fill).toBe(hexToRgb(CATEGORY_COLORS[0]))
  })

  it("affiche le pourcentage au format français", () => {
    expect(cell("Non classé", 0).textContent).toContain("99,3 %")
  })
})

function hexToRgb(hex: string) {
  const [r, g, b] = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16))
  return `rgb(${r}, ${g}, ${b})`
}
