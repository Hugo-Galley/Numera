/** Profil d'ETF personnalisé : le formulaire reprend la recherche à chaque ouverture (la fenêtre reste montée entre deux). */
import { screen } from "@testing-library/react"
import { renderWithProviders } from "@/test/support/render"
import { CustomEtfModal } from "@/components/investments/CustomEtfModal"

const noop = () => {}

describe("CustomEtfModal : préremplissage", () => {
  it("à l'ouverture, ticker et nom reprennent le texte cherché", () => {
    const { rerender } = renderWithProviders(<CustomEtfModal open={false} onOpenChange={noop} initialTicker="" initialName="" />, { auth: true })

    rerender(<CustomEtfModal open onOpenChange={noop} initialTicker="PRIW.PA" initialName="PRIW.PA" />)

    expect(screen.getByLabelText("Ticker / Symbole")).toHaveValue("PRIW.PA")
    expect(screen.getByLabelText("Nom (optionnel)")).toHaveValue("PRIW.PA")
  })

  it("une seconde ouverture avec une autre recherche remplace l'ancienne saisie", async () => {
    const { rerender, user } = renderWithProviders(<CustomEtfModal open onOpenChange={noop} initialTicker="AAA" initialName="AAA" />, { auth: true })
    await user.type(screen.getByLabelText("Ticker / Symbole"), "B")
    rerender(<CustomEtfModal open={false} onOpenChange={noop} initialTicker="AAA" initialName="AAA" />)

    rerender(<CustomEtfModal open onOpenChange={noop} initialTicker="CCC" initialName="CCC" />)

    expect(screen.getByLabelText("Ticker / Symbole")).toHaveValue("CCC")
  })

  it("la saisie en cours n'est pas écrasée tant que la fenêtre reste ouverte", async () => {
    const { user } = renderWithProviders(<CustomEtfModal open onOpenChange={noop} initialTicker="AAA" initialName="" />, { auth: true })

    await user.type(screen.getByLabelText("Ticker / Symbole"), "B")

    expect(screen.getByLabelText("Ticker / Symbole")).toHaveValue("AAAB")
  })
})
