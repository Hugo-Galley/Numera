/** Onglet « Salaire & Aides » : choix de la vue (?vue=aides), configuration du salaire, génération du mois. */
import { screen, waitFor } from "@testing-library/react"
import { http, HttpResponse } from "msw"
import { Route, Routes } from "react-router-dom"
import { WorkTimeProvider } from "@/providers/WorkTimeProvider"
import { apiUrl } from "@/test/handlers"
import { LocationDisplay } from "@/test/LocationDisplay"
import { renderWithProviders } from "@/test/render"
import { server } from "@/test/server"
import { IncomeTab } from "./IncomeTab"

type Body = Record<string, unknown>

const config = { id: 1, salary_account_id: 1, net_salary: 2400, ticket_value: 10.5, ticket_employee_share: 4.2, salary_category_id: null }
const summary = { net_salary: 2400, tt_days_count: 0, ticket_deduction: 0, real_salary: 2400, ticket_credit: 0, is_generated: false, salary_date: "2026-06-25" }

function setup({ route = "/recurring?tab=salary", salaryConfig }: { route?: string; salaryConfig?: () => Response } = {}) {
  server.use(
    http.get(apiUrl("/accounts"), () => HttpResponse.json([{ id: 1, name: "Courant", type: "courant" }])),
    http.get(apiUrl("/categories"), () => HttpResponse.json([])),
    http.get(apiUrl("/salary/config"), salaryConfig ?? (() => HttpResponse.json({ detail: "Not found" }, { status: 404 }))),
    http.get(apiUrl("/salary/work-time"), () =>
      HttpResponse.json({ configured: true, net_salary: 2400, work_days_per_year: 218, work_hours_per_day: 7, hours_per_month: 127, hourly_rate: 18.9 }),
    ),
    http.get(apiUrl("/salary/summary/2026/6"), () => HttpResponse.json(summary)),
    http.get(apiUrl("/salary/telecommuting/2026/6"), () => HttpResponse.json([])),
    http.get(apiUrl("/benefits"), () => HttpResponse.json([])),
    http.get(apiUrl("/benefits/summary"), () => HttpResponse.json({ monthly_expected_total: 0, received_this_year: 0, received_last_12_months: 0, late_count: 0 })),
  )
  return renderWithProviders(
    <WorkTimeProvider>
      <Routes>
        <Route path="/recurring" element={<><IncomeTab /><LocationDisplay /></>} />
      </Routes>
    </WorkTimeProvider>,
    { route, auth: true },
  )
}

const address = () => screen.getByRole("status", { name: "adresse" }).textContent

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["Date"] })
  vi.setSystemTime(new Date("2026-06-15T10:00:00"))
})
afterEach(() => vi.useRealTimers())

describe("IncomeTab : vues", () => {
  it("ouvre le salaire par défaut et passe aux aides en écrivant ?vue=aides", async () => {
    const { user } = setup()
    expect(await screen.findByText("Configuration Salaire & Avantages")).toBeInTheDocument()

    await user.click(screen.getByRole("button", { name: "Aides" }))

    expect(await screen.findByRole("heading", { name: "Aides perçues" })).toBeInTheDocument()
    expect(address()).toBe("/recurring?tab=salary&vue=aides")

    await user.click(screen.getByRole("button", { name: "Salaire" }))
    expect(address()).toBe("/recurring?tab=salary")
  })

  it("ouvre directement les aides avec ?vue=aides (lien du Centre d'Actions)", async () => {
    setup({ route: "/recurring?tab=salary&vue=aides" })
    expect(await screen.findByRole("heading", { name: "Aides perçues" })).toBeInTheDocument()
    expect(screen.queryByText("Configuration Salaire & Avantages")).not.toBeInTheDocument()
  })
})

describe("IncomeTab : salaire", () => {
  it("affiche une erreur (pas un formulaire vide) si la configuration ne charge pas", async () => {
    vi.spyOn(console, "error").mockImplementation(() => undefined)
    setup({ salaryConfig: () => HttpResponse.json({ detail: "boom" }, { status: 500 }) })

    expect(await screen.findByText(/La configuration du salaire n'a pas pu être chargée/)).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: /Sauvegarder/ })).not.toBeInTheDocument()
  })

  it("exige le compte de versement, puis crée la configuration", async () => {
    const posted: Body[] = []
    const { user } = setup()
    server.use(
      http.post(apiUrl("/salary/config"), async ({ request }) => {
        const body = (await request.json()) as Body
        posted.push(body)
        return HttpResponse.json({ ...body, id: 1 })
      }),
    )
    const save = await screen.findByRole("button", { name: /Sauvegarder/ })

    await user.click(save)
    expect(await screen.findByText("Veuillez remplir les champs obligatoires")).toBeInTheDocument()
    expect(posted).toHaveLength(0)

    const [netSalary] = screen.getAllByRole("spinbutton")
    await user.clear(netSalary)
    await user.type(netSalary, "2400")
    await user.click(screen.getAllByRole("combobox")[0])
    await user.click(await screen.findByRole("option", { name: "Courant" }))
    await user.click(screen.getByRole("button", { name: /Sauvegarder/ }))

    expect(await screen.findByText("Configuration sauvegardée")).toBeInTheDocument()
    expect(posted).toEqual([
      { salary_account_id: 1, net_salary: 2400, ticket_value: 10.5, ticket_employee_share: 4.2, salary_category_id: null },
    ])
    expect(await screen.findByRole("button", { name: /Générer les transactions/ })).toBeInTheDocument()
  })

  it("met à jour une configuration existante par PUT", async () => {
    const put: Body[] = []
    const { user } = setup({ salaryConfig: () => HttpResponse.json(config) })
    server.use(
      http.put(apiUrl("/salary/config"), async ({ request }) => {
        const body = (await request.json()) as Body
        put.push(body)
        return HttpResponse.json(body)
      }),
    )

    await user.click(await screen.findByRole("button", { name: /Sauvegarder/ }))

    expect(await screen.findByText("Configuration sauvegardée")).toBeInTheDocument()
    expect(put[0]).toMatchObject({ id: 1, salary_account_id: 1, net_salary: 2400 })
  })

  it("génère le salaire du mois puis propose de réinitialiser", async () => {
    const generated: string[] = []
    const { user } = setup({ salaryConfig: () => HttpResponse.json(config) })
    server.use(
      http.post(apiUrl("/salary/generate/2026/6"), ({ request }) => {
        generated.push(request.method)
        return HttpResponse.json({ status: "generated" })
      }),
    )

    const generate = await screen.findByRole("button", { name: /Générer les transactions/ })
    await waitFor(() => expect(generate).toBeEnabled())
    await user.click(generate)

    expect(await screen.findByText("Transactions générées avec succès !")).toBeInTheDocument()
    expect(screen.getByText("Salaire du mois généré")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Réinitialiser ce mois" })).toBeInTheDocument()
    expect(generated).toEqual(["POST"])
  })

  it("annonce un salaire programmé sans le marquer généré", async () => {
    const { user } = setup({ salaryConfig: () => HttpResponse.json(config) })
    server.use(http.post(apiUrl("/salary/generate/2026/6"), () => HttpResponse.json({ status: "scheduled" })))

    const generate = await screen.findByRole("button", { name: /Générer les transactions/ })
    await waitFor(() => expect(generate).toBeEnabled())
    await user.click(generate)

    expect(await screen.findByText("Salaire programmé : la transaction sera créée le 25/06/2026")).toBeInTheDocument()
    expect(screen.queryByText("Salaire du mois généré")).not.toBeInTheDocument()
  })

  it("affiche l'erreur du serveur si la génération échoue", async () => {
    const { user } = setup({ salaryConfig: () => HttpResponse.json(config) })
    server.use(http.post(apiUrl("/salary/generate/2026/6"), () => HttpResponse.json({ detail: "Mois déjà clôturé" }, { status: 400 })))

    const generate = await screen.findByRole("button", { name: /Générer les transactions/ })
    await waitFor(() => expect(generate).toBeEnabled())
    await user.click(generate)

    expect(await screen.findByText("Mois déjà clôturé")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /Générer les transactions/ })).toBeEnabled()
  })
})
