/** Réglages du prix en heures de travail : préremplissage depuis le fournisseur, validation, enregistrement. */
import { screen, waitFor } from "@testing-library/react"
import { http, HttpResponse } from "msw"
import { apiUrl } from "@/test/support/handlers"
import { renderWithProviders } from "@/test/support/render"
import { server } from "@/test/support/server"
import { WorkTimeSettings } from "@/components/tools/WorkTimeSettings"
import { WorkTimeProvider, type WorkTime } from "@/providers/WorkTimeProvider"

const configured: WorkTime = {
  configured: true, net_salary: 2400, work_days_per_year: 218, work_hours_per_day: 7.5, hours_per_month: 136.25, hourly_rate: 17.62,
}

function setup(workTime: WorkTime | "error" = configured) {
  const patched: unknown[] = []
  server.use(
    http.get(apiUrl("/salary/work-time"), () => (workTime === "error" ? new HttpResponse(null, { status: 500 }) : HttpResponse.json(workTime))),
    http.patch(apiUrl("/salary/work-time"), async ({ request }) => {
      patched.push(await request.json())
      return HttpResponse.json({ ...configured, work_days_per_year: 200 })
    }),
  )
  const view = renderWithProviders(<WorkTimeProvider><WorkTimeSettings /></WorkTimeProvider>, { auth: true })
  return { patched, ...view }
}

describe("WorkTimeSettings", () => {
  it("préremplit jours et heures et affiche le taux horaire", async () => {
    setup()

    expect(await screen.findByDisplayValue("218")).toBeInTheDocument()
    expect(screen.getByDisplayValue("7.5")).toBeInTheDocument()
    expect(screen.getByText(/17,62/)).toBeInTheDocument()
  })

  it("sans salaire configuré : invite à le configurer", async () => {
    setup({ ...configured, configured: false, net_salary: null, hourly_rate: null })

    expect(await screen.findByText("Configurez d'abord votre salaire.")).toBeInTheDocument()
  })

  it("enregistrer : PATCH avec jours entiers et heures à virgule, puis toast", async () => {
    const { user, patched } = setup()
    const days = await screen.findByDisplayValue("218")

    await user.clear(days)
    await user.type(days, "200")
    const hours = screen.getByDisplayValue("7.5")
    await user.clear(hours)
    await user.type(hours, "7.25")
    await user.click(screen.getByRole("button", { name: "Enregistrer" }))

    expect(await screen.findByText("Temps de travail enregistré")).toBeInTheDocument()
    expect(patched).toEqual([{ work_days_per_year: 200, work_hours_per_day: 7.25 }])
  })

  it.each([["0", "7.5"], ["367", "7.5"], ["218", "25"], ["218", "0"]])("valeurs hors limites (%s j, %s h) : refus sans requête", async (d, h) => {
    const { user, patched } = setup()
    const days = await screen.findByDisplayValue("218")

    await user.clear(days)
    await user.type(days, d)
    const hours = screen.getByDisplayValue("7.5")
    await user.clear(hours)
    await user.type(hours, h)
    await user.click(screen.getByRole("button", { name: "Enregistrer" }))

    expect(await screen.findByText("Jours entre 1 et 366, heures entre 0 et 24")).toBeInTheDocument()
    expect(patched).toEqual([])
  })

  it("échec du serveur : toast d'erreur et bouton de nouveau actif", async () => {
    const { user } = setup()
    server.use(http.patch(apiUrl("/salary/work-time"), () => new HttpResponse(null, { status: 500 })))
    await screen.findByDisplayValue("218")

    await user.click(screen.getByRole("button", { name: "Enregistrer" }))

    expect(await screen.findByText("Impossible d'enregistrer le temps de travail")).toBeInTheDocument()
    await waitFor(() => expect(screen.getByRole("button", { name: "Enregistrer" })).toBeEnabled())
  })

  it("réglage non chargé : bouton désactivé", async () => {
    setup("error")

    expect(screen.getByRole("button", { name: "Enregistrer" })).toBeDisabled()
    expect(await screen.findByText(/Impossible de charger/i)).toBeInTheDocument()
  })
})
