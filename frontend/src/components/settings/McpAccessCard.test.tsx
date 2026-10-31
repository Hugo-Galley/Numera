/** Accès MCP : interrupteur global, création d'un token (mot de passe requis, affiché une fois), révocation confirmée. */
import { screen, waitFor, within } from "@testing-library/react"
import { http, HttpResponse } from "msw"
import { makeProfile } from "@/test/factories"
import { apiUrl } from "@/test/handlers"
import { renderWithProviders } from "@/test/render"
import { server } from "@/test/server"
import { McpAccessCard } from "./McpAccessCard"

type Body = Record<string, unknown>

const existing = { id: 3, name: "Claude Code", token_prefix: "nmr_ab12", created_at: "2026-06-01T08:00:00", last_used_at: null }

function setup(tokens: object[] = [existing]) {
  const writes: { method: string; path: string; body: Body | null }[] = []
  let list = tokens
  let listLoads = 0
  server.use(
    http.get(apiUrl("/admin/mcp-tokens"), () => {
      listLoads++
      return HttpResponse.json(list)
    }),
    http.post(apiUrl("/admin/mcp-tokens"), async ({ request }) => {
      const body = (await request.json()) as Body
      writes.push({ method: "POST", path: "/admin/mcp-tokens", body })
      const created = { id: 9, name: body.name, token_prefix: "nmr_zz99", created_at: "2026-06-15T08:00:00", last_used_at: null }
      list = [...list, created]
      return HttpResponse.json({ ...created, token: "nmr_zz99-secret-value" })
    }),
    http.delete(apiUrl("/admin/mcp-tokens/:id"), ({ params }) => {
      writes.push({ method: "DELETE", path: `/admin/mcp-tokens/${params.id}`, body: null })
      list = list.filter((t) => (t as { id: number }).id !== Number(params.id))
      return HttpResponse.json({})
    }),
  )
  const view = renderWithProviders(<McpAccessCard />, { auth: true })
  return { ...view, writes, listLoads: () => listLoads }
}

describe("McpAccessCard : tokens", () => {
  it("exige le mot de passe actuel, affiche le token une seule fois et recharge la liste", async () => {
    const { user, writes, listLoads } = setup()
    await screen.findByText("Claude Code", { selector: "p" })
    const generate = screen.getByRole("button", { name: /Générer un token/ })
    expect(generate).toBeDisabled()

    const name = screen.getByLabelText("Nouveau token")
    await user.clear(name)
    await user.type(name, "Claude Desktop — MacBook")
    await user.type(screen.getByLabelText("Mot de passe actuel"), "admin")
    await user.click(generate)

    expect(await screen.findByText("Copiez-le maintenant : ce token ne sera plus affiché.")).toBeInTheDocument()
    expect(writes).toEqual([{ method: "POST", path: "/admin/mcp-tokens", body: { name: "Claude Desktop — MacBook", current_password: "admin" } }])
    // Nom contenant « desktop » : la configuration Claude Desktop est proposée d'emblée
    expect(screen.getByText(/"NUMERA_AUTH": "Bearer nmr_zz99-secret-value"/)).toBeInTheDocument()
    expect(screen.getByLabelText("Mot de passe actuel")).toHaveValue("")
    await waitFor(() => expect(listLoads()).toBe(2))
    expect(screen.getByText("Claude Desktop — MacBook", { selector: "p" })).toBeInTheDocument()

    await user.click(screen.getByRole("button", { name: "Claude Code" }))
    expect(screen.getByText(/claude mcp add --transport http --scope user numera .*\/mcp --header "Authorization: Bearer nmr_zz99-secret-value"/)).toBeInTheDocument()

    await user.click(screen.getByRole("button", { name: "J'ai copié le token" }))
    expect(screen.queryByText(/nmr_zz99-secret-value/)).not.toBeInTheDocument()
  })

  it("affiche l'erreur du serveur (mot de passe faux) sans afficher de token", async () => {
    const { user } = setup()
    server.use(http.post(apiUrl("/admin/mcp-tokens"), () => HttpResponse.json({ detail: "Mot de passe incorrect" }, { status: 400 })))
    await screen.findByText("Claude Code", { selector: "p" })

    await user.type(screen.getByLabelText("Mot de passe actuel"), "faux")
    await user.click(screen.getByRole("button", { name: /Générer un token/ }))

    expect(await screen.findByText("Mot de passe incorrect")).toBeInTheDocument()
    expect(screen.queryByText(/ce token ne sera plus affiché/)).not.toBeInTheDocument()
    expect(screen.getByRole("button", { name: /Générer un token/ })).toBeEnabled()
  })

  it("ne révoque qu'après confirmation", async () => {
    const { user, writes } = setup()

    await user.click(await screen.findByRole("button", { name: "Révoquer Claude Code" }))
    const dialog = screen.getByRole("dialog", { name: "Révoquer « Claude Code » ?" })
    await user.click(within(dialog).getByRole("button", { name: "Annuler" }))
    expect(writes).toHaveLength(0)

    await user.click(screen.getByRole("button", { name: "Révoquer Claude Code" }))
    await user.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Révoquer" }))

    expect(await screen.findByText("Token « Claude Code » révoqué")).toBeInTheDocument()
    expect(writes).toEqual([{ method: "DELETE", path: "/admin/mcp-tokens/3", body: null }])
    expect(await screen.findByText("Aucun token : générez-en un pour connecter Claude.")).toBeInTheDocument()
  })
})

describe("McpAccessCard : accès global", () => {
  it("active l'accès (PUT /admin/profile) et revient en arrière si le serveur refuse", async () => {
    const puts: Body[] = []
    let mcpEnabled = false
    server.use(
      http.get(apiUrl("/admin/profile"), () => HttpResponse.json(makeProfile({ mcp_enabled: mcpEnabled }))),
      http.put(apiUrl("/admin/profile"), async ({ request }) => {
        const body = (await request.json()) as { mcp_enabled: boolean }
        puts.push(body)
        if (puts.length > 1) return HttpResponse.json({ detail: "Refusé" }, { status: 500 })
        mcpEnabled = body.mcp_enabled
        return HttpResponse.json({})
      }),
    )
    const { user } = setup([])
    const toggle = await screen.findByRole("switch")
    await waitFor(() => expect(toggle).not.toBeChecked())

    await user.click(toggle)
    expect(await screen.findByText("Accès MCP activé")).toBeInTheDocument()
    expect(puts[0]).toEqual({ mcp_enabled: true })
    expect(toggle).toBeChecked()

    await user.click(toggle)
    expect(await screen.findByText("Refusé")).toBeInTheDocument()
    expect(puts[1]).toEqual({ mcp_enabled: false })
    expect(toggle).toBeChecked()
  })
})
