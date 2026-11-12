/** Groupe Sankey d'une catégorie : liste fermée des groupes existants + création d'un nouveau groupe. */
import { screen } from "@testing-library/react"
import { useState } from "react"
import { renderWithProviders } from "@/test/support/render"
import { SankeyGroupSelect, sankeyGroups } from "@/components/classement/CategoriesTab/SankeyGroupSelect"

const GROUPS = ["Loisirs", "Vie courante"]

function Harness({ initial = "", onChange }: { initial?: string; onChange: (v: string) => void }) {
  const [value, setValue] = useState(initial)
  return (
    <SankeyGroupSelect
      id="group"
      value={value}
      groups={GROUPS}
      onChange={(v) => { setValue(v); onChange(v) }}
    />
  )
}

describe("sankeyGroups", () => {
  it("groupes distincts, nettoyés et triés, sans les vides", () => {
    const cats = [
      { group: "Vie courante" },
      { group: " Loisirs " },
      { group: "Vie courante" },
      { group: null },
      { group: "" },
    ]
    expect(sankeyGroups(cats)).toEqual(["Loisirs", "Vie courante"])
  })
})

describe("SankeyGroupSelect", () => {
  it("propose uniquement les groupes existants, « Aucun groupe » et « Nouveau groupe »", async () => {
    const { user } = renderWithProviders(<Harness onChange={() => {}} />)
    await user.click(screen.getByRole("combobox"))
    const options = screen.getAllByRole("option").map((o) => o.textContent?.trim())
    expect(options).toEqual(["Aucun groupe", "Loisirs", "Vie courante", "Nouveau groupe"])
  })

  it("choisir un groupe existant puis revenir à aucun groupe", async () => {
    const onChange = vi.fn()
    const { user } = renderWithProviders(<Harness onChange={onChange} />)
    await user.click(screen.getByRole("combobox"))
    await user.click(screen.getByRole("option", { name: "Loisirs" }))
    expect(onChange).toHaveBeenLastCalledWith("Loisirs")
    expect(screen.getByRole("combobox")).toHaveTextContent("Loisirs")

    await user.click(screen.getByRole("combobox"))
    await user.click(screen.getByRole("option", { name: "Aucun groupe" }))
    expect(onChange).toHaveBeenLastCalledWith("")
  })

  it("« Nouveau groupe » crée un groupe qui devient sélectionné", async () => {
    const onChange = vi.fn()
    const { user } = renderWithProviders(<Harness onChange={onChange} />)
    await user.click(screen.getByRole("combobox"))
    await user.click(screen.getByRole("option", { name: "Nouveau groupe" }))
    await user.type(screen.getByRole("textbox", { name: "Nom du nouveau groupe" }), "  Voyages {Enter}")

    expect(onChange).toHaveBeenLastCalledWith("Voyages")
    expect(screen.getByRole("combobox")).toHaveTextContent("Voyages")
  })

  it("un nouveau groupe qui existe déjà à la casse près réutilise l'existant", async () => {
    const onChange = vi.fn()
    const { user } = renderWithProviders(<Harness onChange={onChange} />)
    await user.click(screen.getByRole("combobox"))
    await user.click(screen.getByRole("option", { name: "Nouveau groupe" }))
    await user.type(screen.getByRole("textbox", { name: "Nom du nouveau groupe" }), "loisirs")
    await user.click(screen.getByRole("button", { name: "Valider le groupe" }))

    expect(onChange).toHaveBeenLastCalledWith("Loisirs")
  })

  it("annuler la création garde la valeur précédente", async () => {
    const onChange = vi.fn()
    const { user } = renderWithProviders(<Harness initial="Loisirs" onChange={onChange} />)
    await user.click(screen.getByRole("combobox"))
    await user.click(screen.getByRole("option", { name: "Nouveau groupe" }))
    await user.type(screen.getByRole("textbox", { name: "Nom du nouveau groupe" }), "Brouillon")
    await user.click(screen.getByRole("button", { name: "Annuler" }))

    expect(onChange).not.toHaveBeenCalled()
    expect(screen.getByRole("combobox")).toHaveTextContent("Loisirs")
  })
})
