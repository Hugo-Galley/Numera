/** Fenêtres du Centre d'Actions : créer une règle de catégorisation, créer et normaliser un marchand. */
import { screen, waitFor } from "@testing-library/react"
import { vi } from "vitest"
import { http, HttpResponse } from "msw"
import { apiUrl } from "@/test/support/handlers"
import { renderWithProviders } from "@/test/support/render"
import { server } from "@/test/support/server"
import { MerchantCreatorModal, RuleCreatorModal } from "@/pages/Audit/CreatorModals"

const courses = { id: 3, name: "Courses", type: "depense" }

describe("RuleCreatorModal", () => {
  function setup(props: Partial<React.ComponentProps<typeof RuleCreatorModal>> = {}) {
    const onCreated = vi.fn()
    const onClose = vi.fn()
    const view = renderWithProviders(
      <RuleCreatorModal merchant="CARTE CARREFOUR" categories={[courses]} onCreated={onCreated} onClose={onClose} {...props} />,
      { auth: true },
    )
    return { onCreated, onClose, ...view }
  }

  it("préremplit le mot-clé avec le marchand et l'annonce dans l'aide", () => {
    setup()

    expect(screen.getByRole("dialog")).toHaveTextContent("Créer une règle d'auto-catégorisation")
    expect(screen.getByDisplayValue("CARTE CARREFOUR")).toBeInTheDocument()
    expect(screen.getByRole("dialog")).toHaveTextContent("CARTE CARREFOUR")
  })

  it("crée la règle : POST avec le mot-clé rogné, puis onCreated et onClose", async () => {
    let body: unknown
    server.use(
      http.post(apiUrl("/categorization-rules/"), async ({ request }) => {
        body = await request.json()
        return HttpResponse.json({ id: 1 })
      }),
    )
    const { user, onCreated, onClose } = setup()

    const pattern = screen.getByDisplayValue("CARTE CARREFOUR")
    await user.clear(pattern)
    await user.type(pattern, "  CARREFOUR  ")
    await user.click(screen.getByRole("button", { name: "Créer la règle" }))

    await waitFor(() => expect(onCreated).toHaveBeenCalledTimes(1))
    expect(onClose).toHaveBeenCalledTimes(1)
    expect(body).toEqual({ pattern: "CARREFOUR", category_id: null, priority: 0 })
    expect(await screen.findByText("Règle créée")).toBeInTheDocument()
  })

  it("catégorie suggérée : elle part dans le corps de la règle", async () => {
    let body: unknown
    server.use(
      http.post(apiUrl("/categorization-rules/"), async ({ request }) => {
        body = await request.json()
        return HttpResponse.json({ id: 1 })
      }),
    )
    const { user, onCreated } = setup({ suggestedCategoryId: 3 })

    await user.click(screen.getByRole("button", { name: "Créer la règle" }))

    await waitFor(() => expect(onCreated).toHaveBeenCalled())
    expect(body).toMatchObject({ pattern: "CARTE CARREFOUR", category_id: 3 })
  })

  it("échec : message d'erreur, la fenêtre reste ouverte", async () => {
    server.use(http.post(apiUrl("/categorization-rules/"), () => HttpResponse.json({ detail: "Règle déjà existante" }, { status: 409 })))
    const { user, onCreated, onClose } = setup()

    await user.click(screen.getByRole("button", { name: "Créer la règle" }))

    expect(await screen.findByText("Règle déjà existante")).toBeInTheDocument()
    expect(onCreated).not.toHaveBeenCalled()
    expect(onClose).not.toHaveBeenCalled()
  })

  it("« Annuler » ferme sans rien envoyer", async () => {
    let posted = false
    server.use(http.post(apiUrl("/categorization-rules/"), () => { posted = true; return HttpResponse.json({}) }))
    const { user, onClose } = setup()

    await user.click(screen.getByRole("button", { name: "Annuler" }))

    expect(onClose).toHaveBeenCalled()
    expect(posted).toBe(false)
  })
})

describe("MerchantCreatorModal", () => {
  function setup(props: Partial<React.ComponentProps<typeof MerchantCreatorModal>> = {}) {
    const onCreated = vi.fn()
    const onClose = vi.fn()
    const view = renderWithProviders(
      <MerchantCreatorModal merchant="CB CARREFOUR 12" categories={[courses]} onCreated={onCreated} onClose={onClose} {...props} />,
      { auth: true },
    )
    return { onCreated, onClose, ...view }
  }

  function serveMerchants() {
    const calls: { path: string; body: unknown }[] = []
    server.use(
      http.post(apiUrl("/merchants"), async ({ request }) => {
        calls.push({ path: "/merchants", body: await request.json() })
        return HttpResponse.json({ id: 1 })
      }),
      http.post(apiUrl("/merchants/auto-normalize"), async ({ request }) => {
        calls.push({ path: "/merchants/auto-normalize", body: await request.json() })
        return HttpResponse.json({})
      }),
    )
    return calls
  }

  it("crée le marchand puis lance la normalisation, avec la seule écriture repérée comme alias", async () => {
    const calls = serveMerchants()
    const { user, onCreated, onClose } = setup()

    const name = screen.getByDisplayValue("CB CARREFOUR 12")
    await user.clear(name)
    await user.type(name, "Carrefour")
    await user.click(screen.getByRole("button", { name: "Créer et normaliser" }))

    await waitFor(() => expect(onCreated).toHaveBeenCalledTimes(1))
    expect(onClose).toHaveBeenCalledTimes(1)
    expect(calls.map((c) => c.path)).toEqual(["/merchants", "/merchants/auto-normalize"])
    expect(calls[0].body).toEqual({ name: "Carrefour", category_id: null, aliases: ["CB CARREFOUR 12"] })
  })

  it("plusieurs variantes repérées : toutes deviennent des alias", async () => {
    const calls = serveMerchants()
    const { user, onCreated } = setup({ variants: ["CB CARREFOUR 12", "CARREFOUR MARKET"] })

    await user.click(screen.getByRole("button", { name: "Créer et normaliser" }))

    await waitFor(() => expect(onCreated).toHaveBeenCalled())
    expect(calls[0].body).toMatchObject({ aliases: ["CB CARREFOUR 12", "CARREFOUR MARKET"] })
  })

  it("échec de la création : message d'erreur, pas de normalisation, fenêtre ouverte", async () => {
    const calls: string[] = []
    server.use(
      http.post(apiUrl("/merchants"), () => HttpResponse.json({ detail: "Nom déjà pris" }, { status: 409 })),
      http.post(apiUrl("/merchants/auto-normalize"), () => { calls.push("normalize"); return HttpResponse.json({}) }),
    )
    const { user, onCreated, onClose } = setup()

    await user.click(screen.getByRole("button", { name: "Créer et normaliser" }))

    expect(await screen.findByText("Nom déjà pris")).toBeInTheDocument()
    expect(calls).toEqual([])
    expect(onCreated).not.toHaveBeenCalled()
    expect(onClose).not.toHaveBeenCalled()
  })

  it("« Annuler » ferme sans rien envoyer", async () => {
    const calls = serveMerchants()
    const { user, onClose } = setup()

    await user.click(screen.getByRole("button", { name: "Annuler" }))

    expect(onClose).toHaveBeenCalled()
    expect(calls).toEqual([])
  })
})
