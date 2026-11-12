/** Classement en anglais : règles, pluriel du résultat d'application, libellés partagés. */
import { screen } from "@testing-library/react"
import { http, HttpResponse } from "msw"
import { setLanguage } from "@/i18n"
import { makeCategory } from "@/test/support/factories"
import { apiUrl } from "@/test/support/handlers"
import { renderWithProviders } from "@/test/support/render"
import { server } from "@/test/support/server"
import { RulesTab } from "@/components/classement/RulesTab"

function serve(rules: object[]) {
  server.use(
    http.get(apiUrl("/categorization-rules/"), () => HttpResponse.json(rules)),
    http.get(apiUrl("/categories"), () => HttpResponse.json([makeCategory({ id: 3, name: "Transport" })])),
    http.post(apiUrl("/categorization-rules/apply-all"), () => HttpResponse.json({ modified_count: 1 })),
  )
}

describe("RulesTab en anglais", () => {
  afterEach(() => setLanguage("fr"))

  it("état vide, titre et bouton", async () => {
    await setLanguage("en")
    serve([])
    renderWithProviders(<RulesTab />, { auth: true })
    expect(await screen.findByText("Auto-categorization Rules")).toBeInTheDocument()
    expect(screen.getByText(/No rule defined/)).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /Apply to existing/ })).toBeInTheDocument()
  })

  it("règle listée : priorité et pluriel de l'application (1 transaction)", async () => {
    await setLanguage("en")
    serve([{ id: 1, pattern: "UBER", category_id: 3, merchant_name: "Uber", transaction_type: "Sortie", priority: 5 }])
    const { user } = renderWithProviders(<RulesTab />, { auth: true })
    expect(await screen.findByText("Priority: 5")).toBeInTheDocument()
    await user.click(screen.getByRole("button", { name: /Apply to existing/ }))
    expect(await screen.findByText("1 transaction updated")).toBeInTheDocument()
  })
})
