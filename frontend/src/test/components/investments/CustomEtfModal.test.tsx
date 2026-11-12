/** Profil d'ETF personnalisé : composition récupérée sur Yahoo à partir du ticker ou de l'ISIN. */
import { screen, waitFor } from "@testing-library/react"
import { vi } from "vitest"
import { http, HttpResponse } from "msw"
import { apiUrl } from "@/test/support/handlers"
import { renderWithProviders } from "@/test/support/render"
import { server } from "@/test/support/server"
import { CustomEtfModal } from "@/components/investments/CustomEtfModal"

function setup(props: Partial<React.ComponentProps<typeof CustomEtfModal>> = {}) {
  const onOpenChange = vi.fn()
  const onProfileCreated = vi.fn()
  const view = renderWithProviders(<CustomEtfModal open onOpenChange={onOpenChange} onProfileCreated={onProfileCreated} {...props} />, { auth: true })
  return { onOpenChange, onProfileCreated, ...view }
}
const submit = () => screen.getByRole("button", { name: "Créer depuis Yahoo" })

describe("CustomEtfModal", () => {
  it("sans ticker ni ISIN : le bouton est désactivé", () => {
    setup()

    expect(submit()).toBeDisabled()
  })

  it("ticker saisi : POST de la décomposition (champs vides omis), profil transmis, fenêtre fermée", async () => {
    let body: unknown
    server.use(http.post(apiUrl("/etf-profiles/auto-decompose"), async ({ request }) => { body = await request.json(); return HttpResponse.json({ id: 8, name: "Amundi Prime", ticker: "PRIW.PA", isin: "IE00BKX55T58" }) }))
    const { user, onProfileCreated, onOpenChange } = setup()

    await user.type(screen.getByLabelText("Ticker / Symbole"), "PRIW.PA")
    await user.type(screen.getByLabelText("Nom (optionnel)"), "  Amundi Prime ")
    await user.click(submit())

    await waitFor(() => expect(onProfileCreated).toHaveBeenCalledTimes(1))
    expect(body).toEqual({ symbol: "PRIW.PA", name: "Amundi Prime" })
    expect(onProfileCreated.mock.calls[0][0]).toMatchObject({ id: 8, ticker: "PRIW.PA" })
    expect(onOpenChange).toHaveBeenCalledWith(false)
    expect(await screen.findByText("Amundi Prime décomposé avec succès !")).toBeInTheDocument()
  })

  it("valeurs initiales : ISIN prérempli et envoyé avec le ticker saisi", async () => {
    let body: unknown
    server.use(http.post(apiUrl("/etf-profiles/auto-decompose"), async ({ request }) => { body = await request.json(); return HttpResponse.json({ id: 8, name: "X", ticker: "PRIW.PA" }) }))
    const { user } = setup({ initialIsin: "IE00BKX55T58" })
    expect(screen.getByLabelText("Code ISIN (Optionnel)")).toHaveValue("IE00BKX55T58")
    // Le bouton reste désactivé tant que le ticker est vide, même avec un ISIN
    expect(submit()).toBeDisabled()

    await user.type(screen.getByLabelText("Ticker / Symbole"), "PRIW.PA")
    await user.click(submit())
    await waitFor(() => expect(body).toEqual({ symbol: "PRIW.PA", isin: "IE00BKX55T58" }))
  })

  it("réponse sans profil : message d'échec, fenêtre ouverte", async () => {
    server.use(http.post(apiUrl("/etf-profiles/auto-decompose"), () => HttpResponse.json({})))
    const { user, onProfileCreated, onOpenChange } = setup()

    await user.type(screen.getByLabelText("Ticker / Symbole"), "ZZZ")
    await user.click(submit())

    expect(await screen.findByText("Impossible de décomposer ce fonds en ligne")).toBeInTheDocument()
    expect(onProfileCreated).not.toHaveBeenCalled()
    expect(onOpenChange).not.toHaveBeenCalled()
  })

  it("erreur serveur : message du serveur", async () => {
    server.use(http.post(apiUrl("/etf-profiles/auto-decompose"), () => HttpResponse.json({ detail: "Yahoo indisponible" }, { status: 502 })))
    const { user } = setup()

    await user.type(screen.getByLabelText("Ticker / Symbole"), "ZZZ")
    await user.click(submit())

    expect(await screen.findByText("Yahoo indisponible")).toBeInTheDocument()
  })

  it("« Annuler » ferme sans rien envoyer", async () => {
    const { user, onOpenChange } = setup()

    await user.click(screen.getByRole("button", { name: "Annuler" }))

    expect(onOpenChange).toHaveBeenCalledWith(false)
  })
})
