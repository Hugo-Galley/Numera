/** Mot de passe : mot de passe actuel exigé, confirmation avant déconnexion, une erreur 400 reste sur la page. */
import { screen, within } from "@testing-library/react"
import { http, HttpResponse } from "msw"
import { safeStorage } from "@/lib/storage"
import { apiUrl } from "@/test/handlers"
import { renderWithProviders } from "@/test/render"
import { server } from "@/test/server"
import { PasswordCard } from "./ProfileForm"

function servePut(response: () => Response) {
  const bodies: unknown[] = []
  server.use(
    http.put(apiUrl("/admin/profile"), async ({ request }) => {
      bodies.push(await request.json())
      return response()
    }),
  )
  return bodies
}

async function fill(user: ReturnType<typeof renderWithProviders>["user"], current: string, next = "nouveau-secret", confirm = next) {
  if (current) await user.type(screen.getByLabelText("Mot de passe actuel"), current)
  await user.type(screen.getByLabelText("Nouveau mot de passe"), next)
  await user.type(screen.getByLabelText("Confirmer le mot de passe"), confirm)
  await user.click(screen.getByRole("button", { name: "Enregistrer" }))
}

describe("PasswordCard", () => {
  it("sans mot de passe actuel : message, aucune requête", async () => {
    const bodies = servePut(() => HttpResponse.json({}))
    const { user } = renderWithProviders(<PasswordCard />, { auth: true })

    await fill(user, "")

    expect(await screen.findByText("Saisis ton mot de passe actuel")).toBeInTheDocument()
    expect(bodies).toEqual([])
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument()
  })

  it("confirmation différente ou trop court : refusé avant envoi", async () => {
    const bodies = servePut(() => HttpResponse.json({}))
    const { user } = renderWithProviders(<PasswordCard />, { auth: true })

    await fill(user, "ancien", "nouveau-secret", "autre-secret")
    expect(await screen.findByText("Les mots de passe ne correspondent pas")).toBeInTheDocument()
    expect(bodies).toEqual([])
  })

  it("succès : confirmation de déconnexion puis PUT { password, current_password }", async () => {
    const bodies = servePut(() => HttpResponse.json({}))
    const { user } = renderWithProviders(<PasswordCard />, { auth: true })

    await fill(user, "ancien")
    const dialog = await screen.findByRole("dialog", { name: /Confirmation de modification/ })
    await user.click(within(dialog).getByRole("button", { name: "Confirmer et se déconnecter" }))

    expect(await screen.findByText("Profil mis à jour")).toBeInTheDocument()
    expect(bodies).toEqual([{ password: "nouveau-secret", current_password: "ancien" }])
  })

  it("erreur 400 (mot de passe actuel faux) : message affiché, reste sur la page, session conservée", async () => {
    servePut(() => HttpResponse.json({ detail: "Mot de passe actuel incorrect" }, { status: 400 }))
    const { user } = renderWithProviders(<PasswordCard />, { auth: true })
    const token = safeStorage.getItem("token")

    await fill(user, "faux")
    await user.click(within(await screen.findByRole("dialog")).getByRole("button", { name: "Confirmer et se déconnecter" }))

    expect(await screen.findByText("Mot de passe actuel incorrect")).toBeInTheDocument()
    expect(safeStorage.getItem("token")).toBe(token)
    expect(screen.getByLabelText("Mot de passe actuel")).toHaveValue("faux")
    expect(screen.getByRole("button", { name: "Enregistrer" })).toBeEnabled()
  })
})
