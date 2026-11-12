/** Onglet Conseils : score de santé, indicateurs, analyses du backend et rejet définitif d'un conseil. */
import { screen, waitFor } from "@testing-library/react"
import { http, HttpResponse } from "msw"
import { apiUrl } from "@/test/support/handlers"
import { renderWithProviders } from "@/test/support/render"
import { server } from "@/test/support/server"
import { InsightsTab } from "@/components/dashboard/tabs/InsightsTab"

const insights = {
  health_score: {
    total_score: 82.4,
    metrics: [
      { name: "Taux d'épargne", value: 22.5, unit: "%", status: "good" },
      { name: "Fonds d'urgence", value: 4, unit: "mois", status: "warning" },
      { name: "Solde moyen", value: 1480.99, unit: "€", status: "bad" },
    ],
  },
  insights: [
    { key: "a", type: "anomaly", title: "Dépense inhabituelle", description: "Garage : 900 €", value: 900 },
    { key: "b", type: "positive", title: "Épargne en hausse", description: "+12 % ce mois", value: 12, unit: "%" },
  ],
}

describe("InsightsTab", () => {
  it("affiche le score arrondi et chaque indicateur avec son unité (« mois » traduit, montants en euros)", () => {
    renderWithProviders(<InsightsTab insights={insights} />, { auth: true })

    expect(screen.getByText("82")).toBeInTheDocument()
    expect(screen.getByText("Santé Financière")).toBeInTheDocument()
    expect(screen.getByText("Taux d'épargne")).toBeInTheDocument()
    expect(screen.getByText(/22,5\s%/)).toBeInTheDocument()
    expect(screen.getByText(/4\smois/)).toBeInTheDocument()
    expect(screen.getByText(/1\s480,99/)).toBeInTheDocument()
  })

  it("liste les conseils : une anomalie en « +montant », un point positif avec sa valeur et son unité", () => {
    renderWithProviders(<InsightsTab insights={insights} />, { auth: true })

    expect(screen.getByText("Dépense inhabituelle")).toBeInTheDocument()
    expect(screen.getAllByText(/\+900,00/).length).toBeGreaterThan(0)
    expect(screen.getByText("Épargne en hausse")).toBeInTheDocument()
    expect(screen.getAllByText(/12\s%/).length).toBeGreaterThan(0)
  })

  it("sans conseil : message « tout semble sous contrôle »", () => {
    renderWithProviders(<InsightsTab insights={{ health_score: { total_score: 40, metrics: [] }, insights: [] }} />, { auth: true })

    expect(screen.getByText(/Tout semble sous contrôle/)).toBeInTheDocument()
  })

  it("données absentes : score à 0 et liste vide, sans erreur", () => {
    renderWithProviders(<InsightsTab insights={null} />, { auth: true })

    expect(screen.getByText("0")).toBeInTheDocument()
    expect(screen.getByText(/Tout semble sous contrôle/)).toBeInTheDocument()
  })

  it("rejeter un conseil : il disparaît tout de suite et le rejet est envoyé au serveur", async () => {
    let body: unknown
    server.use(http.post(apiUrl("/analytics/insights/dismiss"), async ({ request }) => { body = await request.json(); return HttpResponse.json({}) }))
    const { user } = renderWithProviders(<InsightsTab insights={insights} />, { auth: true })

    await user.click(screen.getAllByTitle("Ne pas prendre en compte de façon permanente")[0])

    expect(screen.queryByText("Dépense inhabituelle")).not.toBeInTheDocument()
    await waitFor(() => expect(body).toEqual({ key: "a" }))
    expect(screen.getByText("Épargne en hausse")).toBeInTheDocument()
  })

  it("rejet refusé par le serveur : le conseil revient et un message prévient", async () => {
    server.use(http.post(apiUrl("/analytics/insights/dismiss"), () => HttpResponse.json({ detail: "KO" }, { status: 500 })))
    const { user } = renderWithProviders(<InsightsTab insights={insights} />, { auth: true })

    await user.click(screen.getAllByTitle("Ne pas prendre en compte de façon permanente")[0])

    expect(await screen.findByText("Impossible de masquer cet insight")).toBeInTheDocument()
    expect(await screen.findByText("Dépense inhabituelle")).toBeInTheDocument()
  })
})
