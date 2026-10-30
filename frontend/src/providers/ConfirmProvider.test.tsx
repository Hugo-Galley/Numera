import { useState } from "react"
import { screen, waitFor } from "@testing-library/react"
import { renderWithProviders } from "@/test/render"
import { useConfirm } from "./ConfirmProvider"

type Options = Parameters<ReturnType<typeof useConfirm>>[1]

/** Bouton qui demande une confirmation et affiche chaque réponse reçue. */
function Asker({ options }: { options?: Options }) {
  const confirm = useConfirm()
  const [answers, setAnswers] = useState<string[]>([])
  const ask = (message: string) => confirm(message, options).then((ok) => setAnswers((a) => [...a, `${message}=${ok}`]))
  return (
    <div>
      <button onClick={() => ask("Supprimer le compte ?")}>Demander</button>
      <button onClick={() => ask("Autre question ?")}>Redemander</button>
      <p>réponses : {answers.join(", ")}</p>
    </div>
  )
}

const answers = () => screen.getByText(/^réponses :/)

describe("ConfirmProvider", () => {
  it("affiche le message avec le titre et le bouton par défaut", async () => {
    const { user } = renderWithProviders(<Asker />)
    await user.click(screen.getByRole("button", { name: "Demander" }))

    const dialog = await screen.findByRole("dialog", { name: "Confirmer" })
    expect(dialog).toHaveTextContent("Supprimer le compte ?")
    expect(screen.getByRole("button", { name: "Supprimer" })).toHaveFocus()
  })

  it("résout true sur le bouton de confirmation et ferme la boîte", async () => {
    const { user } = renderWithProviders(<Asker />)
    await user.click(screen.getByRole("button", { name: "Demander" }))
    await user.click(await screen.findByRole("button", { name: "Supprimer" }))

    await waitFor(() => expect(answers()).toHaveTextContent("Supprimer le compte ?=true"))
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument()
  })

  it("résout false sur Annuler", async () => {
    const { user } = renderWithProviders(<Asker />)
    await user.click(screen.getByRole("button", { name: "Demander" }))
    await user.click(await screen.findByRole("button", { name: "Annuler" }))

    await waitFor(() => expect(answers()).toHaveTextContent("Supprimer le compte ?=false"))
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument()
  })

  it("résout false sur Échap", async () => {
    const { user } = renderWithProviders(<Asker />)
    await user.click(screen.getByRole("button", { name: "Demander" }))
    await screen.findByRole("dialog")

    await user.keyboard("{Escape}")

    await waitFor(() => expect(answers()).toHaveTextContent("Supprimer le compte ?=false"))
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument()
  })

  it("une seule réponse par demande (pas de double résolution)", async () => {
    const { user } = renderWithProviders(<Asker />)
    await user.click(screen.getByRole("button", { name: "Demander" }))
    await user.click(await screen.findByRole("button", { name: "Supprimer" }))
    await user.click(screen.getByRole("button", { name: "Demander" }))
    await user.click(await screen.findByRole("button", { name: "Annuler" }))

    await waitFor(() =>
      expect(answers()).toHaveTextContent("réponses : Supprimer le compte ?=true, Supprimer le compte ?=false"),
    )
  })

  it("une nouvelle demande pendant qu'une autre est ouverte résout la précédente à false", async () => {
    // demande ouverte puis remplacée sans clic sur la boîte (ex. deux actions successives par programme)
    function Twice() {
      const confirm = useConfirm()
      const [log, setLog] = useState<string[]>([])
      const push = (entry: string) => setLog((l) => [...l, entry])
      const run = () => {
        void confirm("Première ?").then((ok) => push(`première=${ok}`))
        void confirm("Seconde ?").then((ok) => push(`seconde=${ok}`))
      }
      return (
        <div>
          <button onClick={run}>Deux demandes</button>
          <p>journal : {log.join(", ")}</p>
        </div>
      )
    }
    const { user } = renderWithProviders(<Twice />)
    await user.click(screen.getByRole("button", { name: "Deux demandes" }))

    expect(await screen.findByRole("dialog")).toHaveTextContent("Seconde ?")
    await waitFor(() => expect(screen.getByText(/^journal :/)).toHaveTextContent("première=false"))

    await user.click(screen.getByRole("button", { name: "Supprimer" }))
    await waitFor(() => expect(screen.getByText(/^journal :/)).toHaveTextContent("journal : première=false, seconde=true"))
  })

  it("respecte titre et libellé personnalisés ; non destructif → « Confirmer »", async () => {
    const { user, unmount } = renderWithProviders(<Asker options={{ title: "Clôturer le mois", confirmLabel: "Clôturer" }} />)
    await user.click(screen.getByRole("button", { name: "Demander" }))
    expect(await screen.findByRole("dialog", { name: "Clôturer le mois" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Clôturer" })).toBeInTheDocument()
    unmount()

    const second = renderWithProviders(<Asker options={{ destructive: false }} />)
    await second.user.click(screen.getByRole("button", { name: "Demander" }))
    await second.user.click(await screen.findByRole("button", { name: "Confirmer" }))
    await waitFor(() => expect(answers()).toHaveTextContent("=true"))
  })
})
