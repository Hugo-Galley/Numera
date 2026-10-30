/** Import CSV : upload du fichier (aperçu), catégories inconnues, commit et compte rendu (doublons, erreurs). */
import { screen, waitFor, within } from "@testing-library/react"
import { http, HttpResponse } from "msw"
import { apiUrl } from "@/test/handlers"
import { renderWithProviders } from "@/test/render"
import { server } from "@/test/server"
import type { PreviewData } from "./types"
import { ImportFlow } from "./index"

const PREVIEW: PreviewData = {
  filename: "releve.csv",
  total_rows: 3,
  invalid_rows: 1,
  warnings: ["Colonne « Note » ignorée"],
  delimiter: ";",
  preview: [
    { Date: "15/06/2026", Type: "Sortie", Commercant: "Carrefour", Categorie: "Courses", Montant: "42,50" },
    { Date: "16/06/2026", Type: "Sortie", Commercant: "Inconnu", Categorie: "Loisirs", Montant: "abc", error: "montant invalide", line: 3 },
  ],
  unknown_categories: ["Loisirs"],
}

interface Upload {
  path: string
  authorization: string | null
  contentType: string | null
  fields: [string, FormDataEntryValue][]
}

/** Comptes, catégories et les deux routes d'upload. jsdom n'envoie pas le multipart à MSW : les champs sont lus sur le FormData construit. */
function serveImport({ preview = PREVIEW, result = { imported: 2, skipped: 1, errors: 0, error_details: [] } as object } = {}) {
  const uploads: Upload[] = []
  const appended: [string, FormDataEntryValue][] = []
  const append = FormData.prototype.append as (name: string, value: string | Blob) => void
  vi.spyOn(FormData.prototype, "append").mockImplementation(function (this: FormData, name: string, value: string | Blob) {
    appended.push([name, value as FormDataEntryValue])
    return append.call(this, name, value)
  })
  const record = (request: Request) => {
    uploads.push({
      path: new URL(request.url).pathname,
      authorization: request.headers.get("authorization"),
      contentType: request.headers.get("content-type"),
      fields: appended.splice(0),
    })
  }
  server.use(
    http.get(apiUrl("/accounts"), () =>
      HttpResponse.json([
        { id: 1, name: "Compte joint", type: "courant", active: true },
        { id: 2, name: "Ancien livret", type: "epargne", active: false },
      ]),
    ),
    http.get(apiUrl("/categories"), () => HttpResponse.json([{ id: 7, name: "Sorties" }])),
    http.post(apiUrl("/import/preview"), ({ request }) => {
      record(request)
      return HttpResponse.json(preview)
    }),
    http.post(apiUrl("/import/commit"), ({ request }) => {
      record(request)
      return HttpResponse.json(result)
    }),
  )
  return uploads
}

const csv = () => new File(["Date;Type;Commercant;Montant\n"], "releve.csv", { type: "text/csv" })
const fileInput = (container: HTMLElement) => container.querySelector<HTMLInputElement>('input[type="file"]')!

async function choosePreview(accountId?: number, onImported = vi.fn()) {
  const view = renderWithProviders(<ImportFlow accountId={accountId} onImported={onImported} />, { auth: true })
  await view.user.upload(fileInput(view.container), csv())
  await screen.findByText("Aperçu des données")
  return { ...view, onImported }
}

describe("ImportFlow : aperçu", () => {
  it("avant tout fichier : état d'attente, import impossible", async () => {
    serveImport()
    renderWithProviders(<ImportFlow accountId={1} />, { auth: true })

    expect(screen.getByText("Aucun fichier en attente")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Lancer l'importation" })).toBeDisabled()
    expect(await screen.findByText("Compte joint")).toBeInTheDocument()
  })

  it("upload : fichier envoyé (Bearer, sans Content-Type JSON), aperçu, lignes invalides et avertissements", async () => {
    const uploads = serveImport()
    await choosePreview(1)

    expect(uploads).toHaveLength(1)
    expect(uploads[0].path).toBe("/import/preview")
    expect(uploads[0].authorization).toMatch(/^Bearer /)
    expect(uploads[0].contentType).not.toBe("application/json")
    expect(uploads[0].fields.map(([name]) => name)).toEqual(["file"])
    expect((uploads[0].fields[0][1] as File).name).toBe("releve.csv")

    const table = screen.getByRole("table")
    expect(within(table).getByText("Carrefour")).toBeInTheDocument()
    expect(within(table).getByText("Ligne 3 : montant invalide")).toBeInTheDocument()
    expect(screen.getByText("Lignes invalides (ignorées)")).toBeInTheDocument()
    expect(screen.getByText("Colonne « Note » ignorée")).toBeInTheDocument()
    expect(screen.getAllByText("releve.csv").length).toBeGreaterThan(0)
  })

  it("aperçu en échec : message du serveur, pas d'aperçu", async () => {
    serveImport()
    server.use(http.post(apiUrl("/import/preview"), () => HttpResponse.json({ detail: "En-têtes introuvables" }, { status: 400 })))
    const { user, container } = renderWithProviders(<ImportFlow accountId={1} />, { auth: true })

    await user.upload(fileInput(container), csv())

    expect(await screen.findByText("En-têtes introuvables")).toBeInTheDocument()
    expect(screen.getByText("Aucun fichier en attente")).toBeInTheDocument()
  })

  it("chargement des comptes en échec : toast d'erreur", async () => {
    serveImport()
    server.use(http.get(apiUrl("/accounts"), () => HttpResponse.json({ detail: "boom" }, { status: 500 })))
    renderWithProviders(<ImportFlow />, { auth: true })

    expect(await screen.findByText("Erreur chargement données initiales")).toBeInTheDocument()
  })
})

describe("ImportFlow : commit", () => {
  it("envoie compte, option et correspondance des catégories ; compte rendu des doublons ; onImported appelé", async () => {
    const uploads = serveImport()
    const { user, onImported } = await choosePreview(1)

    await user.click(screen.getByRole("combobox"))
    await user.click(screen.getByRole("option", { name: "Sorties" }))
    await user.click(screen.getByRole("button", { name: "Lancer l'importation" }))

    expect(await screen.findByText("Importation réussie")).toBeInTheDocument()
    expect(uploads[1].path).toBe("/import/commit")
    const fields = Object.fromEntries(uploads[1].fields.filter(([name]) => name !== "file"))
    expect(fields).toEqual({ account_id: "1", create_missing_categories: "true", category_mapping: JSON.stringify({ Loisirs: 7 }) })
    expect(uploads[1].fields.find(([name]) => name === "file")).toBeDefined()
    expect(screen.getByText("Doublons").nextSibling).toHaveTextContent("1")
    expect(screen.getByText("Transactions").nextSibling).toHaveTextContent("2")
    expect(screen.getByText("Import terminé avec succès")).toBeInTheDocument()
    expect(onImported).toHaveBeenCalledTimes(1)
  })

  it("catégorie inconnue laissée sur « Créer nouvelle », option décochée : envoyés tels quels", async () => {
    const uploads = serveImport()
    const { user } = await choosePreview(1)

    expect(screen.getByRole("combobox")).toHaveTextContent("Créer nouvelle")
    await user.click(screen.getByLabelText("Créer les catégories manquantes"))
    await user.click(screen.getByRole("button", { name: "Lancer l'importation" }))

    await screen.findByText("Importation réussie")
    const fields = Object.fromEntries(uploads[1].fields)
    expect(fields.create_missing_categories).toBe("false")
    expect(fields.category_mapping).toBe(JSON.stringify({ Loisirs: "CREATE" }))
  })

  it("que des doublons : 0 importée, onImported non appelé", async () => {
    serveImport({ result: { imported: 0, skipped: 3, errors: 0, error_details: [] } })
    const { user, onImported } = await choosePreview(1)

    await user.click(screen.getByRole("button", { name: "Lancer l'importation" }))

    expect(await screen.findByText("Doublons")).toBeInTheDocument()
    expect(screen.getByText("Doublons").nextSibling).toHaveTextContent("3")
    expect(onImported).not.toHaveBeenCalled()
  })

  it("erreurs de lignes : import partiel et détail par ligne", async () => {
    serveImport({ result: { imported: 1, skipped: 0, errors: 3, error_details: [{ line: 4, reason: "date invalide" }] } })
    const { user } = await choosePreview(1)

    await user.click(screen.getByRole("button", { name: "Lancer l'importation" }))

    expect(await screen.findByText("Importation partielle")).toBeInTheDocument()
    expect(screen.getByText("Ligne 4")).toBeInTheDocument()
    expect(screen.getByText("… et 2 autre(s)")).toBeInTheDocument()
  })

  it("commit en échec : message du serveur, l'aperçu reste affiché", async () => {
    serveImport()
    server.use(http.post(apiUrl("/import/commit"), () => HttpResponse.json({ detail: "Compte introuvable" }, { status: 404 })))
    const { user, onImported } = await choosePreview(1)

    await user.click(screen.getByRole("button", { name: "Lancer l'importation" }))

    expect(await screen.findByText("Compte introuvable")).toBeInTheDocument()
    expect(screen.getByText("Aperçu des données")).toBeInTheDocument()
    expect(onImported).not.toHaveBeenCalled()
  })

  it("sans compte présélectionné : seuls les comptes actifs sont proposés, import bloqué tant qu'aucun n'est choisi", async () => {
    const uploads = serveImport()
    const { user } = await choosePreview()

    const [accountSelect] = screen.getAllByRole("combobox")
    expect(screen.getByRole("button", { name: "Lancer l'importation" })).toBeDisabled()
    await user.click(accountSelect)
    expect(screen.queryByRole("option", { name: /Ancien livret/ })).not.toBeInTheDocument()
    await user.click(screen.getByRole("option", { name: /Compte joint/ }))
    await user.click(screen.getByRole("button", { name: "Lancer l'importation" }))

    await waitFor(() => expect(uploads).toHaveLength(2))
    expect(Object.fromEntries(uploads[1].fields).account_id).toBe("1")
  })
})
