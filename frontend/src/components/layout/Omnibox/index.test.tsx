import { screen, waitFor } from "@testing-library/react"
import { Route, Routes } from "react-router-dom"
import { formatCurrency } from "@/lib/utils"
import { makeAccount } from "@/test/factories"
import { listAccounts } from "@/test/handlers/accounts"
import { searchTransactions } from "@/test/handlers/transactions"
import { LocationDisplay } from "@/test/LocationDisplay"
import { renderWithProviders } from "@/test/render"
import { server } from "@/test/server"
import { Omnibox } from "."

const mainAccount = { ...makeAccount({ id: 7, name: "Compte joint" }), active: true, is_main: true }

function renderOmnibox(accounts: object[] = [mainAccount]) {
  server.use(listAccounts(accounts), searchTransactions())
  return renderWithProviders(
    <>
      <Omnibox />
      <Routes>
        <Route path="*" element={<LocationDisplay />} />
      </Routes>
    </>,
    { route: "/", auth: true },
  )
}

async function openWithShortcut(user: ReturnType<typeof renderOmnibox>["user"]) {
  await user.keyboard("{Meta>}k{/Meta}")
  return screen.findByPlaceholderText("Rechercher, ou saisir « 12,50 boulangerie »…")
}

const address = () => screen.getByRole("status", { name: "adresse" }).textContent
/** Bouton « Ajouter une dépense de 12,50 € · boulangerie » (le libellé contient aussi le compte visé). */
const quickEntryButton = (label: string) => screen.findByRole("button", { name: new RegExp(`^${label}`) })

describe("Omnibox : ouverture", () => {
  it("fermée au départ, ⌘K l'ouvre et charge les comptes", async () => {
    const { user } = renderOmnibox()
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument()

    const input = await openWithShortcut(user)

    expect(screen.getByRole("dialog", { name: "Recherche" })).toBeInTheDocument()
    expect(input).toHaveFocus()
    // l'action « Nouvelle transaction » annonce le compte principal une fois les comptes chargés
    expect(await screen.findByRole("button", { name: /^Nouvelle transaction\s*Compte joint/ })).toBeInTheDocument()
  })

  it("Ctrl+K l'ouvre aussi (Windows, Linux)", async () => {
    const { user } = renderOmnibox()

    await user.keyboard("{Control>}k{/Control}")

    expect(await screen.findByRole("dialog", { name: "Recherche" })).toBeInTheDocument()
  })
})

describe("Omnibox : saisie rapide", () => {
  it("« 12,50 boulangerie » propose une dépense sur le compte principal et ouvre sa création", async () => {
    const { user } = renderOmnibox()
    await user.type(await openWithShortcut(user), "12,50 boulangerie")

    const button = await quickEntryButton(`Ajouter une dépense de ${formatCurrency(12.5)} · boulangerie`)
    expect(button).toHaveTextContent("Sur Compte joint, à vérifier avant d'enregistrer")
    await user.click(button)

    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument())
    expect(address()).toBe("/accounts/7?new=tx&type=Sortie&amount=12.5&merchant=boulangerie")
  })

  it("« 1 234 loyer » (milliers) propose 1 234 €, pas 1 € ni 234 €", async () => {
    const { user } = renderOmnibox()
    await user.type(await openWithShortcut(user), "1 234 loyer")

    await user.click(await quickEntryButton(`Ajouter une dépense de ${formatCurrency(1234)} · loyer`))

    expect(address()).toBe("/accounts/7?new=tx&type=Sortie&amount=1234&merchant=loyer")
  })

  it("« +1200 prime » propose un revenu, validé par Entrée", async () => {
    const { user } = renderOmnibox()
    await user.type(await openWithShortcut(user), "+1200 prime")
    await quickEntryButton(`Ajouter un revenu de ${formatCurrency(1200)} · prime`)

    await user.keyboard("{Enter}")

    expect(address()).toBe("/accounts/7?new=tx&type=Entree&amount=1200&merchant=prime")
  })

  it("sans compte principal, se rabat sur le premier compte courant actif", async () => {
    const courant = { ...makeAccount({ id: 3, name: "Courant perso" }), active: true }
    const { user } = renderOmnibox([{ ...makeAccount({ name: "Livret A", type: "epargne" }), active: true }, courant])
    await user.type(await openWithShortcut(user), "8 café")

    await user.click(await quickEntryButton(`Ajouter une dépense de ${formatCurrency(8)} · café`))

    expect(address()).toBe("/accounts/3?new=tx&type=Sortie&amount=8&merchant=caf%C3%A9")
  })

  it("sans compte courant actif, prévient au lieu de naviguer", async () => {
    const { user } = renderOmnibox([{ ...makeAccount({ type: "courant" }), active: false }])
    await user.type(await openWithShortcut(user), "12 pain")

    const button = await quickEntryButton(`Ajouter une dépense de ${formatCurrency(12)} · pain`)
    expect(button).toHaveTextContent("Aucun compte courant actif")
    await user.click(button)

    expect(await screen.findByText("Aucun compte courant actif pour enregistrer la transaction")).toBeInTheDocument()
    expect(address()).toBe("/")
  })

  it("un texte sans montant ne propose pas de saisie rapide", async () => {
    const { user } = renderOmnibox()
    await user.type(await openWithShortcut(user), "boulangerie")

    await waitFor(() => expect(screen.queryByText("Saisie rapide")).not.toBeInTheDocument())
    expect(screen.queryByRole("button", { name: /^Ajouter une dépense/ })).not.toBeInTheDocument()
  })
})
