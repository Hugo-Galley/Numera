/** Palette des graphiques de répartition : distincte, lisible en clair et en sombre, « Non classé » neutre. */
import { CATEGORY_COLORS, NEUTRAL_COLOR, UNCLASSIFIED_NAME, categoryColor } from "@/lib/chartPalette"

const luminance = (hex: string) => {
  const [r, g, b] = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255)
    .map((c) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4))
  return 0.2126 * r + 0.7152 * g + 0.0722 * b
}
const contrast = (a: string, b: string) => {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x)
  return (hi + 0.05) / (lo + 0.05)
}
const SLATE = ["#0f172a", "#1e293b", "#334155", "#475569", "#64748b", "#7c8ba1", "#94a3b8", "#b6c0cc", "#cbd5e1"]

describe("palette catégorielle", () => {
  it("a des teintes toutes différentes, sans gris ardoise", () => {
    expect(new Set(CATEGORY_COLORS).size).toBe(CATEGORY_COLORS.length)
    expect(CATEGORY_COLORS.length).toBeGreaterThanOrEqual(7)
    for (const c of CATEGORY_COLORS) expect(SLATE).not.toContain(c.toLowerCase())
  })

  it("reste lisible sur fond blanc et sur fond sombre (contraste ≥ 3:1)", () => {
    for (const c of CATEGORY_COLORS) {
      expect(contrast(c, "#ffffff")).toBeGreaterThanOrEqual(3)
      expect(contrast(c, "#0f172a")).toBeGreaterThanOrEqual(3)
    }
  })

  it("donne une couleur neutre à « Non classé » et tourne sur la palette sinon", () => {
    expect(categoryColor(0, UNCLASSIFIED_NAME)).toBe(NEUTRAL_COLOR)
    expect(categoryColor(0, "Actions")).toBe(CATEGORY_COLORS[0])
    expect(categoryColor(CATEGORY_COLORS.length + 1)).toBe(CATEGORY_COLORS[1])
  })
})
