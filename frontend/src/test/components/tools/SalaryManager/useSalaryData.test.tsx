/** Salaire : chargement de la configuration, mois affiché, jours de télétravail, génération et réinitialisation. */
import type { ReactNode } from "react"
import { act, renderHook, screen, waitFor } from "@testing-library/react"
import { format } from "date-fns"
import { http, HttpResponse } from "msw"
import { resetApiCache } from "@/lib/apiCache"
import { Toaster } from "@/components/ui/sonner"
import { WorkTimeProvider } from "@/providers/WorkTimeProvider"
import { useSalaryData } from "@/components/tools/SalaryManager/useSalaryData"
import { apiUrl } from "@/test/support/handlers"
import { server } from "@/test/support/server"

const wrapper = ({ children }: { children: ReactNode }) => (
  <WorkTimeProvider>{children}<Toaster /></WorkTimeProvider>
)

const serverConfig = { id: 1, salary_account_id: 3, salary_category_id: 9, ticket_account_id: null, ticket_category_id: null, net_salary: 2500, ticket_value: 10, ticket_employee_share: 4 }
const summary = (over: object = {}) => ({ net_salary: 2500, tt_days_count: 2, ticket_deduction: 8, real_salary: 2492, ticket_credit: 0, salary_date: "2026-06-28", is_generated: false, ...over })

interface Setup { config?: object | null | "error"; summary?: object | "error"; ttDays?: object[] }

function serve({ config = serverConfig, summary: sum = summary(), ttDays = [{ date: "2026-06-10" }] }: Setup = {}) {
  const calls: { method: string; path: string; body?: unknown }[] = []
  const record = async (request: Request) => {
    const text = await request.text()
    calls.push({ method: request.method, path: new URL(request.url).pathname.replace(/^.*\/(salary)/, "/$1"), body: text ? JSON.parse(text) : undefined })
  }
  server.use(
    http.get(apiUrl("/accounts"), () => HttpResponse.json([{ id: 3, name: "Courant", type: "courant" }])),
    http.get(apiUrl("/categories"), () => HttpResponse.json([{ id: 9, name: "Salaire" }])),
    http.get(apiUrl("/salary/work-time"), () => HttpResponse.json({})),
    http.get(apiUrl("/salary/config"), () => {
      if (config === "error") return new HttpResponse(null, { status: 500 })
      if (config === null) return HttpResponse.json({ detail: "Aucune configuration" }, { status: 404 })
      return HttpResponse.json(config)
    }),
    http.get(apiUrl("/salary/summary/:y/:m"), () => (sum === "error" ? new HttpResponse(null, { status: 500 }) : HttpResponse.json(sum))),
    http.get(apiUrl("/salary/telecommuting/:y/:m"), () => HttpResponse.json(ttDays)),
    http.post(apiUrl("/salary/config"), async ({ request }) => { await record(request.clone()); return HttpResponse.json({ ...serverConfig, id: 5, net_salary: 3000 }) }),
    http.put(apiUrl("/salary/config"), async ({ request }) => { await record(request.clone()); return HttpResponse.json({ ...serverConfig, net_salary: 2700 }) }),
    http.put(apiUrl("/salary/telecommuting/:y/:m"), async ({ request }) => { await record(request.clone()); return HttpResponse.json({}) }),
    http.put(apiUrl("/salary/months/:y/:m"), async ({ request }) => { await record(request.clone()); return HttpResponse.json({}) }),
    http.post(apiUrl("/salary/generate/:y/:m"), async ({ request }) => { await record(request.clone()); return HttpResponse.json({ status: "generated" }) }),
    http.delete(apiUrl("/salary/generate/:y/:m"), async ({ request }) => { await record(request.clone()); return HttpResponse.json({}) }),
  )
  return calls
}

const ready = async (result: { current: ReturnType<typeof useSalaryData> }, withMonth = true) => {
  await waitFor(() => expect(result.current.loading).toBe(false))
  if (withMonth) await waitFor(() => expect(result.current.summary).not.toBeNull())
}

describe("useSalaryData", () => {
  beforeEach(() => { vi.spyOn(console, "error").mockImplementation(() => {}) })

  it("charge comptes, catégories, configuration puis le mois (date de versement, jours TT, tickets)", async () => {
    serve()
    const { result } = renderHook(() => useSalaryData(), { wrapper })
    await ready(result)

    expect(result.current.accounts).toHaveLength(1)
    expect(result.current.categories).toHaveLength(1)
    expect(result.current.config).toMatchObject({ id: 1, salary_account_id: 3, ticket_account_id: "", ticket_category_id: "", net_salary: 2500 })
    expect(result.current.salaryDate?.getDate()).toBe(28)
    expect(result.current.ttDays).toHaveLength(1)
    expect(result.current.nbTickets).toBe(2)
    expect(result.current.isGenerated).toBe(false)
    expect(result.current.configError).toBe(false)
  })

  it("404 sur la configuration : formulaire par défaut, sans erreur ni chargement du mois", async () => {
    serve({ config: null })
    const { result } = renderHook(() => useSalaryData(), { wrapper })
    await ready(result, false)

    expect(result.current.config).toMatchObject({ net_salary: 2000, salary_account_id: "" })
    expect(result.current.config.id).toBeUndefined()
    expect(result.current.configError).toBe(false)
    expect(result.current.summary).toBeNull()
    expect(result.current.nbTickets).toBe(0)
  })

  it("autre erreur sur la configuration : blocage de l'édition et toast", async () => {
    serve({ config: "error" })
    const { result } = renderHook(() => useSalaryData(), { wrapper })
    await ready(result, false)

    expect(result.current.configError).toBe(true)
    expect(await screen.findByText("Impossible de charger la configuration du salaire")).toBeInTheDocument()
  })

  it("échec du chargement du mois : état vidé, drapeau levé, et les jours ne sont plus modifiables", async () => {
    const calls = serve({ summary: "error" })
    const { result } = renderHook(() => useSalaryData(), { wrapper })
    await waitFor(() => expect(result.current.monthLoadFailed).toBe(true))

    expect(result.current.summary).toBeNull()
    expect(result.current.ttDays).toEqual([])
    await act(() => result.current.handleToggleDay(new Date(2026, 5, 11)))
    expect(calls).toEqual([])
  })

  it("mois déjà généré : l'interface reflète is_generated et refuse jours et date", async () => {
    const calls = serve({ summary: summary({ is_generated: true }) })
    const { result } = renderHook(() => useSalaryData(), { wrapper })
    await ready(result)

    expect(result.current.isGenerated).toBe(true)
    await act(() => result.current.handleToggleDay(new Date(2026, 5, 11)))
    await act(() => result.current.handleSalaryDateChange(new Date(2026, 5, 20)))
    expect(calls).toEqual([])
  })

  it("enregistrer sans compte de versement : refus sans requête", async () => {
    const calls = serve({ config: null })
    const { result } = renderHook(() => useSalaryData(), { wrapper })
    await ready(result, false)

    await act(() => result.current.handleSaveConfig())

    expect(await screen.findByText("Veuillez remplir les champs obligatoires")).toBeInTheDocument()
    expect(calls).toEqual([])
    expect(result.current.saving).toBe(false)
  })

  it("première configuration : POST avec identifiants numériques, ticket omis, puis configuration serveur reprise", async () => {
    const calls = serve({ config: null })
    const { result } = renderHook(() => useSalaryData(), { wrapper })
    await ready(result, false)

    act(() => result.current.setConfig({ ...result.current.config, salary_account_id: 3, salary_category_id: 9 }))
    await act(() => result.current.handleSaveConfig())

    const post = calls.find((c) => c.method === "POST")!
    expect(post.body).toMatchObject({ salary_account_id: 3, salary_category_id: 9, net_salary: 2000 })
    expect(post.body).not.toHaveProperty("ticket_account_id")
    await waitFor(() => expect(result.current.config).toMatchObject({ id: 5, net_salary: 3000 }))
    expect(await screen.findByText("Configuration sauvegardée")).toBeInTheDocument()
  })

  it("configuration existante : PUT, catégorie vide envoyée à null", async () => {
    const calls = serve()
    const { result } = renderHook(() => useSalaryData(), { wrapper })
    await ready(result)

    act(() => result.current.setConfig({ ...result.current.config, salary_category_id: "", ticket_account_id: 3 }))
    await act(() => result.current.handleSaveConfig())

    const put = calls.find((c) => c.method === "PUT")!
    expect(put.body).toMatchObject({ salary_category_id: null, ticket_account_id: 3 })
    await waitFor(() => expect(result.current.config.net_salary).toBe(2700))
  })

  it("échec de sauvegarde : toast d'erreur et indicateur retombé", async () => {
    serve()
    server.use(http.put(apiUrl("/salary/config"), () => new HttpResponse(null, { status: 500 })))
    const { result } = renderHook(() => useSalaryData(), { wrapper })
    await ready(result)

    await act(() => result.current.handleSaveConfig())

    expect(await screen.findByText("Impossible de sauvegarder")).toBeInTheDocument()
    expect(result.current.saving).toBe(false)
  })

  it("basculer un jour de télétravail : ajout puis retrait envoyés au format yyyy-MM-dd", async () => {
    const calls = serve({ ttDays: [] })
    const { result } = renderHook(() => useSalaryData(), { wrapper })
    await ready(result)
    const month = result.current.currentDate.getMonth() + 1
    const day = new Date(result.current.currentDate.getFullYear(), month - 1, 11)

    // Le mois est relu après l'écriture : la liste locale revient à l'état du serveur (ici figé), seul le corps du PUT compte
    await act(() => result.current.handleToggleDay(day))
    const put = calls.find((c) => c.path.startsWith("/salary/telecommuting"))!
    expect(put.body).toEqual({ dates: [expect.stringMatching(/^\d{4}-\d{2}-11$/)] })

    // Jour déjà posé sur le serveur : un nouveau clic le retire
    server.use(http.get(apiUrl("/salary/telecommuting/:y/:m"), () => HttpResponse.json([{ date: format(day, "yyyy-MM-dd") }])))
    resetApiCache() // lecture mise en cache 30 s
    await act(() => result.current.loadMonthData(result.current.currentDate))
    await waitFor(() => expect(result.current.ttDays).toHaveLength(1))
    await act(() => result.current.handleToggleDay(day))
    expect(calls.filter((c) => c.path.startsWith("/salary/telecommuting")).slice(-1)[0].body).toEqual({ dates: [] })
  })

  it("jour de télétravail : échec du PUT, toast et relecture du mois", async () => {
    serve({ ttDays: [] })
    server.use(http.put(apiUrl("/salary/telecommuting/:y/:m"), () => new HttpResponse(null, { status: 500 })))
    const { result } = renderHook(() => useSalaryData(), { wrapper })
    await ready(result)

    await act(() => result.current.handleToggleDay(new Date(result.current.currentDate.getFullYear(), result.current.currentDate.getMonth(), 11)))

    expect(await screen.findByText("Impossible de sauvegarder le jour")).toBeInTheDocument()
    await waitFor(() => expect(result.current.ttDays).toEqual([]))
  })

  it("changer la date de versement : PUT du mois ; échec : toast", async () => {
    const calls = serve()
    const { result } = renderHook(() => useSalaryData(), { wrapper })
    await ready(result)

    await act(() => result.current.handleSalaryDateChange(new Date(2026, 5, 20)))
    expect(calls.find((c) => c.path.startsWith("/salary/months"))!.body).toEqual({ salary_date: "2026-06-20" })

    server.use(http.put(apiUrl("/salary/months/:y/:m"), () => new HttpResponse(null, { status: 500 })))
    await act(() => result.current.handleSalaryDateChange(new Date(2026, 5, 21)))
    expect(await screen.findByText("Impossible de sauvegarder la date")).toBeInTheDocument()
  })

  it("générer : exige une date, puis POST et mois marqué généré", async () => {
    const calls = serve({ summary: summary({ salary_date: null }) })
    const { result } = renderHook(() => useSalaryData(), { wrapper })
    await ready(result)

    await act(() => result.current.handleGenerate())
    expect(await screen.findByText("Veuillez définir une date de versement")).toBeInTheDocument()
    expect(calls).toEqual([])

    act(() => result.current.setSalaryDate(new Date(2026, 5, 28)))
    await act(() => result.current.handleGenerate())

    expect(calls.some((c) => c.method === "POST" && c.path.startsWith("/salary/generate"))).toBe(true)
    expect(result.current.isGenerated).toBe(true)
    expect(result.current.generating).toBe(false)
  })

  it("génération planifiée : message avec la date, mois non marqué généré", async () => {
    serve()
    server.use(http.post(apiUrl("/salary/generate/:y/:m"), () => HttpResponse.json({ status: "scheduled" })))
    const { result } = renderHook(() => useSalaryData(), { wrapper })
    await ready(result)

    await act(() => result.current.handleGenerate())

    expect(result.current.isGenerated).toBe(false)
    expect(await screen.findByText(/28\/06\/2026/)).toBeInTheDocument()
  })

  it("génération en erreur : message du serveur", async () => {
    serve()
    server.use(http.post(apiUrl("/salary/generate/:y/:m"), () => HttpResponse.json({ detail: "Compte clos" }, { status: 400 })))
    const { result } = renderHook(() => useSalaryData(), { wrapper })
    await ready(result)

    await act(() => result.current.handleGenerate())

    expect(await screen.findByText("Compte clos")).toBeInTheDocument()
    expect(result.current.generating).toBe(false)
  })

  it("réinitialiser : DELETE puis mois repassé en non généré ; erreur : message du serveur", async () => {
    const calls = serve({ summary: summary({ is_generated: true }) })
    const { result } = renderHook(() => useSalaryData(), { wrapper })
    await ready(result)

    await act(() => result.current.handleReset())
    expect(calls.some((c) => c.method === "DELETE")).toBe(true)
    expect(result.current.isGenerated).toBe(false)
    expect(await screen.findByText("Mois réinitialisé !")).toBeInTheDocument()

    server.use(http.delete(apiUrl("/salary/generate/:y/:m"), () => HttpResponse.json({ detail: "Déjà versé" }, { status: 409 })))
    await act(() => result.current.handleReset())
    expect(await screen.findByText("Déjà versé")).toBeInTheDocument()
  })
})
