/** Placement du Sankey : colonnes par profondeur, liens ordonnés, hauteur minimale, mode étroit. */
import { computeLayout, NARROW_WIDTH, type SankeyData } from "@/components/analytics/sankeyLayout"

const data: SankeyData = {
  nodes: [
    { name: "Salaire" },
    { name: "Budget" },
    { name: "Épargne", color: "#10b981" },
    { name: "Fixe" },
    { name: "Loisirs" },
    { name: "Logement", category_id: 13 },
    { name: "Énergie", category_id: 14 },
    { name: "Sortie", category_id: 4 },
    { name: "Orphelin" },
  ],
  links: [
    { source: 0, target: 1, value: 3000 },
    { source: 1, target: 2, value: 500 },
    { source: 1, target: 3, value: 1200 },
    { source: 1, target: 4, value: 300 },
    { source: 3, target: 5, value: 900 },
    { source: 3, target: 6, value: 300 },
    { source: 4, target: 7, value: 300 },
    { source: 4, target: 99, value: 10 }, // cible hors limites : ignorée
    { source: 2, target: 2, value: 0 }, // valeur nulle : ignorée
  ],
}

describe("computeLayout", () => {
  const layout = computeLayout(data, 900)
  const node = (name: string) => layout.nodes.find((n) => n.name === name)!

  it("garde les nœuds reliés, écarte l'orphelin et les liens invalides", () => {
    expect(layout.nodes.map((n) => n.name)).not.toContain("Orphelin")
    expect(layout.links).toHaveLength(7)
  })

  it("une colonne par profondeur : source à gauche, catégories à droite", () => {
    expect(node("Salaire").depth).toBe(0)
    expect(node("Budget").depth).toBe(1)
    expect(node("Fixe").depth).toBe(2)
    expect(node("Logement").depth).toBe(3)
    expect(node("Salaire").x).toBeLessThan(node("Budget").x)
    expect(node("Fixe").x).toBeLessThan(node("Logement").x)
  })

  it("valeurs, hauteurs et positions cohérentes ; les enfants descendent sous leur parent", () => {
    expect(node("Budget").value).toBe(3000)
    expect(node("Budget").height).toBeGreaterThan(node("Fixe").height)
    for (const n of layout.nodes) {
      expect(Number.isFinite(n.y)).toBe(true)
      expect(n.height).toBeGreaterThan(0)
    }
    expect(node("Logement").y).toBeLessThan(node("Sortie").y)
    for (const l of layout.links) {
      expect(l.width).toBeGreaterThan(0)
      expect(Number.isFinite(l.sy) && Number.isFinite(l.ty)).toBe(true)
    }
    expect(layout.height).toBeGreaterThanOrEqual(240)
    expect(node("Épargne").color).toBe("#10b981")
  })

  it("écran étroit signalé sous NARROW_WIDTH", () => {
    expect(layout.narrow).toBe(false)
    expect(computeLayout(data, NARROW_WIDTH - 1).narrow).toBe(true)
  })
})
