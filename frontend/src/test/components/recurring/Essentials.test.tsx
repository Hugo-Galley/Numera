/** Classement essentiel / non essentiel d'une récurrence et carte « Reste à vivre ». */
import { screen, waitFor } from "@testing-library/react"
import { http, HttpResponse } from "msw"
import { describe, expect, it, vi } from "vitest"
import { EssentialToggle } from "@/components/recurring/EssentialToggle"
import { EssentialsSummary } from "@/components/recurring/EssentialsSummary"
import { safeStorage } from "@/lib/storage"
import { apiUrl } from "@/test/support/handlers"
import { renderWithProviders } from "@/test/support/render"
import { server } from "@/test/support/server"

const reste = {
  revenus_recurrents: 2500, charges_essentielles: 900, charges_non_essentielles: 45,
  reste_a_vivre_essentiel: 1600, reste_a_vivre_total: 1555,
}

function servePatches() {
  const bodies: unknown[] = []
  server.use(http.patch(apiUrl("/recurring-transactions/:id"), async ({ request }) => {
    bodies.push(await request.json()); return HttpResponse.json({})
  }))
  return bodies
}

describe("EssentialToggle", () => {
  it("valeur automatique : l'indique et enregistre un choix manuel", async () => {
    const bodies = servePatches()
    const onChanged = vi.fn()
    const { user } = renderWithProviders(
      <EssentialToggle sub={{ name: "MAIF", recurring_id: 7, is_essential: true, is_essential_source: "auto" }} onChanged={onChanged} />,
      { auth: true },
    )
    expect(screen.getByText("(auto)")).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: /valeur automatique/ })).not.toBeInTheDocument()

    await user.click(screen.getByRole("switch", { name: "MAIF : charge essentielle" }))
    await waitFor(() => expect(onChanged).toHaveBeenCalled())
    expect(bodies).toEqual([{ is_essential: false }])
  })

  it("choix manuel : revient à la valeur automatique (null)", async () => {
    const bodies = servePatches()
    const { user } = renderWithProviders(
      <EssentialToggle sub={{ name: "Claude", recurring_id: 8, is_essential: true, is_essential_source: "manual" }} onChanged={() => {}} />,
      { auth: true },
    )
    expect(screen.queryByText("(auto)")).not.toBeInTheDocument()
    await user.click(screen.getByRole("button", { name: /valeur automatique/ }))
    await waitFor(() => expect(bodies).toEqual([{ is_essential: null }]))
  })

  it("abonnement détecté (sans récurrence) : rien à classer", () => {
    renderWithProviders(<EssentialToggle sub={{ name: "Spotify", recurring_id: null }} onChanged={() => {}} />)
    expect(screen.queryByRole("switch")).not.toBeInTheDocument()
  })
})

describe("EssentialsSummary", () => {
  it("affiche les totaux et le reste à vivre, essentiels seulement par défaut puis toutes les charges (mémorisé)", async () => {
    safeStorage.removeItem("reste-a-vivre-mode")
    server.use(http.get(apiUrl("/analytics/reste-a-vivre"), () => HttpResponse.json(reste)))
    const { user } = renderWithProviders(
      <EssentialsSummary totals={{ essential: { monthly: 900, annual: 10800 }, non_essential: { monthly: 45, annual: 540 } }} />,
      { auth: true },
    )
    expect(await screen.findByText(/1\s?600,00/)).toBeInTheDocument()
    expect(screen.getByText(/Ce que tu pourrais couper : 45,00/)).toBeInTheDocument()
    expect(screen.getByText(/10\s?800,00/)).toBeInTheDocument()

    await user.click(screen.getByRole("button", { name: "Toutes les charges" }))
    expect(screen.getByText(/1\s?555,00/)).toBeInTheDocument()
    expect(safeStorage.getItem("reste-a-vivre-mode")).toBe("all")
  })

  it("reprend le mode mémorisé", async () => {
    safeStorage.setItem("reste-a-vivre-mode", "all")
    server.use(http.get(apiUrl("/analytics/reste-a-vivre"), () => HttpResponse.json(reste)))
    renderWithProviders(<EssentialsSummary totals={{}} />, { auth: true })
    expect(await screen.findByText(/1\s?555,00/)).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Toutes les charges" })).toHaveAttribute("aria-pressed", "true")
  })
})
