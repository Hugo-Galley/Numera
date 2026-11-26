/** Parts du donut de répartition : 7 lignes nommées au plus, le reste (dont les libellés non classés) en « Autres ». */
import { buildSlices, MAX_NAMED_SLICES } from "@/components/investments/AccountBreakdown/slices"
import { NEUTRAL_COLOR } from "@/lib/chartPalette"

describe("buildSlices", () => {
  it("garde les 7 plus grosses lignes et regroupe le reste, part non décomposée comprise", () => {
    const rows = Array.from({ length: 10 }, (_, i) => ({ name: `Société ${i}`, value: 10 - i }))
    const slices = buildSlices(rows, 100, "Autres entreprises")

    expect(slices).toHaveLength(MAX_NAMED_SLICES + 1)
    expect(slices[0]).toMatchObject({ name: "Société 0", value: 10, share: 10, isOther: false })
    const other = slices[slices.length - 1]
    // 100 − (10 + 9 + … + 4) = 51 : lignes 8 à 10 et part non couverte
    expect(other).toMatchObject({ name: "Autres entreprises", value: 51, share: 51, color: NEUTRAL_COLOR, isOther: true })
  })

  it("trie par valeur et range « Non renseigné » dans « Autres »", () => {
    const slices = buildSlices([{ name: "Non renseigné", value: 30 }, { name: "Apple", value: 20 }, { name: "Total", value: 50 }], 100, "Autres")
    expect(slices.map((s) => [s.name, s.value])).toEqual([["Total", 50], ["Apple", 20], ["Autres", 30]])
  })

  it("sans reste : pas de part « Autres » ; compte vide : aucune part", () => {
    expect(buildSlices([{ name: "Bitcoin", value: 40 }, { name: "Ethereum", value: 60 }], 100, "Autres").map((s) => s.name)).toEqual(["Ethereum", "Bitcoin"])
    expect(buildSlices([], 0, "Autres")).toEqual([])
  })
})
