/** Sauvegarde : état affiché (configurée, en retard, absente), sauvegarde manuelle réussie ou échouée. */
import { screen, waitFor, within } from "@testing-library/react"
import { http, HttpResponse } from "msw"
import { apiUrl } from "@/test/handlers"
import { renderWithProviders } from "@/test/render"
import { server } from "@/test/server"
import { BackupCard } from "./BackupCard"

const status = {
  configured: true,
  last_backup_at: "2026-06-15T07:00:00",
  last_backup_file: "numera-20260615.db.enc",
  encrypted: true,
  backup_count: 7,
  last_auto_success_at: "2026-06-15T07:00:00",
  last_error: null,
  last_error_at: null,
  github_configured: false,
  github_last_sync_at: null,
  github_error: null,
  stale: false,
}

function setup(current: object = status, run: () => Response | Promise<Response> = () => HttpResponse.json({ ok: true, github: true })) {
  let statusLoads = 0
  const runs: string[] = []
  server.use(
    http.get(apiUrl("/admin/backup/status"), () => {
      statusLoads++
      return HttpResponse.json(current)
    }),
    http.post(apiUrl("/admin/backup/run"), ({ request }) => {
      runs.push(request.method)
      return run()
    }),
  )
  const view = renderWithProviders(<BackupCard />, { auth: true })
  return { ...view, runs, statusLoads: () => statusLoads }
}

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["Date"] })
  vi.setSystemTime(new Date("2026-06-15T10:00:00"))
})
afterEach(() => vi.useRealTimers())

describe("BackupCard", () => {
  it("affiche l'état de la dernière sauvegarde", async () => {
    setup()

    expect(await screen.findAllByText(/il y a 3 h/)).toHaveLength(2)
    expect(screen.getByText("Chiffrée (BACKUP_KEY)")).toBeInTheDocument()
    expect(screen.getByText("Non configurée")).toBeInTheDocument()
    expect(screen.getByText("7")).toBeInTheDocument()
  })

  it("signale une sauvegarde en retard avec l'erreur", async () => {
    setup({ ...status, stale: true, last_error: "disque plein", last_backup_at: "2026-06-10T07:00:00" })

    expect(await screen.findByText(/Aucune sauvegarde depuis plus de 2 jours\. Erreur : disque plein/)).toBeInTheDocument()
    expect(screen.getByText(/il y a 5 jours/)).toBeInTheDocument()
  })

  it("explique l'absence de sauvegarde sur le serveur", async () => {
    setup({ ...status, configured: false })

    expect(await screen.findByText(/Aucune sauvegarde trouvée sur ce serveur/)).toBeInTheDocument()
  })

  it("lance une sauvegarde : bouton désactivé pendant l'envoi, résultat GitHub, état rechargé", async () => {
    let release!: () => void
    const gate = new Promise<void>((resolve) => (release = resolve))
    const { user, runs, statusLoads } = setup(status, async () => {
      await gate
      return HttpResponse.json({ ok: true, github: true })
    })
    await waitFor(() => expect(statusLoads()).toBe(1))

    await user.click(screen.getByRole("button", { name: "Sauvegarder maintenant" }))
    expect(await screen.findByRole("button", { name: "Sauvegarde en cours..." })).toBeDisabled()
    release()

    const dialog = await screen.findByRole("dialog", { name: "Sauvegarde terminée" })
    expect(within(dialog).getByText("La sauvegarde a été créée et envoyée sur GitHub.")).toBeInTheDocument()
    expect(runs).toEqual(["POST"])
    await waitFor(() => expect(statusLoads()).toBe(2))
  })

  it("affiche le message du serveur si la sauvegarde échoue", async () => {
    const { user } = setup(status, () => HttpResponse.json({ detail: "BACKUP_KEY manquante" }, { status: 500 }))

    await user.click(await screen.findByRole("button", { name: "Sauvegarder maintenant" }))

    const dialog = await screen.findByRole("dialog", { name: "Sauvegarde échouée" })
    expect(within(dialog).getByText("BACKUP_KEY manquante")).toBeInTheDocument()
    await user.click(within(dialog).getByRole("button", { name: "Fermer" }))
    expect(screen.getByRole("button", { name: "Sauvegarder maintenant" })).toBeEnabled()
  })
})
