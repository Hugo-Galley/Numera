/** Identifiant et photo de profil : la photo se change librement, l'identifiant exige le mot de passe actuel et une confirmation. */
import { screen, waitFor, within } from "@testing-library/react"
import { http, HttpResponse } from "msw"
import { makeProfile } from "@/test/support/factories"
import { apiUrl } from "@/test/support/handlers"
import { renderWithProviders } from "@/test/support/render"
import { server } from "@/test/support/server"
import { ProfileInfoCard } from "@/components/settings/ProfileForm"

function setup(profile = makeProfile({ username: "admin", profile_picture_url: "https://exemple.test/moi.png" })) {
  const bodies: unknown[] = []
  server.use(
    http.get(apiUrl("/admin/profile"), () => HttpResponse.json(profile)),
    http.put(apiUrl("/admin/profile"), async ({ request }) => { bodies.push(await request.json()); return HttpResponse.json({}) }),
  )
  return { bodies, ...renderWithProviders(<ProfileInfoCard />, { auth: true }) }
}

describe("ProfileInfoCard", () => {
  it("préremplit l'identifiant et la photo du profil, et affiche la photo", async () => {
    setup()

    expect(await screen.findByDisplayValue("admin")).toBeInTheDocument()
    expect(screen.getByDisplayValue("https://exemple.test/moi.png")).toBeInTheDocument()
    expect(screen.getByRole("img", { name: "Profil" })).toHaveAttribute("src", "https://exemple.test/moi.png")
  })

  it("photo seule : PUT sans identifiant ni mot de passe, aucune confirmation de déconnexion", async () => {
    const { user, bodies } = setup()
    const url = await screen.findByLabelText("URL de la photo de profil")
    // le profil arrive après le premier rendu et réécrit les champs : attendre le préremplissage avant de saisir
    await waitFor(() => expect(url).toHaveValue("https://exemple.test/moi.png"))

    await user.clear(url)
    await user.type(url, "https://exemple.test/nouvelle.png")
    await user.click(screen.getByRole("button", { name: "Enregistrer" }))

    await waitFor(() => expect(bodies).toEqual([{ profile_picture_url: "https://exemple.test/nouvelle.png" }]))
    expect(await screen.findByText("Profil mis à jour")).toBeInTheDocument()
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument()
  })

  it("photo vidée : la chaîne vide part au serveur (c'est ainsi qu'on la retire)", async () => {
    const { user, bodies } = setup()
    const url = await screen.findByLabelText("URL de la photo de profil")
    await waitFor(() => expect(url).toHaveValue("https://exemple.test/moi.png"))
    await user.clear(url)
    await user.click(screen.getByRole("button", { name: "Enregistrer" }))

    await waitFor(() => expect(bodies).toEqual([{ profile_picture_url: "" }]))
  })

  it("sans photo : une icône remplace l'image", async () => {
    setup(makeProfile({ username: "admin", profile_picture_url: null }))
    await screen.findByDisplayValue("admin")

    expect(screen.queryByRole("img", { name: "Profil" })).not.toBeInTheDocument()
  })

  it("changer l'identifiant fait apparaître le champ du mot de passe actuel ; sans lui, refusé avant envoi", async () => {
    const { user, bodies } = setup()
    const username = await screen.findByLabelText("Nom d'utilisateur")
    expect(screen.queryByLabelText("Mot de passe actuel")).not.toBeInTheDocument()

    await user.clear(username)
    await user.type(username, "hugo")
    expect(screen.getByLabelText("Mot de passe actuel")).toBeInTheDocument()
    await user.click(screen.getByRole("button", { name: "Enregistrer" }))

    expect(await screen.findByText("Saisis ton mot de passe actuel pour changer d'identifiant")).toBeInTheDocument()
    expect(bodies).toEqual([])
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument()
  })

  it("changement d'identifiant : confirmation de déconnexion, puis PUT avec l'identifiant et le mot de passe actuel", async () => {
    const { user, bodies } = setup()
    const username = await screen.findByLabelText("Nom d'utilisateur")
    await waitFor(() => expect(username).toHaveValue("admin"))
    await user.clear(username)
    await user.type(username, "hugo")
    await user.type(screen.getByLabelText("Mot de passe actuel"), "secret")
    await user.click(screen.getByRole("button", { name: "Enregistrer" }))

    const dialog = await screen.findByRole("dialog", { name: /Confirmation de modification/ })
    expect(dialog).toHaveTextContent("déconnexion immédiate")
    expect(bodies).toEqual([])
    await user.click(within(dialog).getByRole("button", { name: "Confirmer et se déconnecter" }))

    await waitFor(() => expect(bodies).toEqual([{ profile_picture_url: "https://exemple.test/moi.png", username: "hugo", current_password: "secret" }]))
    expect(await screen.findByText("Déconnexion en cours suite au changement d'identifiants...")).toBeInTheDocument()
  })

  it("« Annuler » dans la confirmation : rien n'est envoyé", async () => {
    const { user, bodies } = setup()
    const username = await screen.findByLabelText("Nom d'utilisateur")
    await user.clear(username)
    await user.type(username, "hugo")
    await user.type(screen.getByLabelText("Mot de passe actuel"), "secret")
    await user.click(screen.getByRole("button", { name: "Enregistrer" }))

    await user.click(within(await screen.findByRole("dialog")).getByRole("button", { name: "Annuler" }))

    expect(bodies).toEqual([])
  })

  it("refus du serveur : message du serveur", async () => {
    const { user } = setup()
    server.use(http.put(apiUrl("/admin/profile"), () => HttpResponse.json({ detail: "Mot de passe incorrect" }, { status: 403 })))
    const url = await screen.findByLabelText("URL de la photo de profil")

    await user.type(url, "x")
    await user.click(screen.getByRole("button", { name: "Enregistrer" }))

    expect(await screen.findByText("Mot de passe incorrect")).toBeInTheDocument()
  })
})
