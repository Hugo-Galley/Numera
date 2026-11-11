/** Omnibox (⌘K) : destinations, actions et saisie rapide dans la langue choisie ; la recherche porte sur le texte affiché. */
import { screen } from "@testing-library/react"
import { setLanguage } from "@/i18n"
import { makeAccount } from "@/test/support/factories"
import { listAccounts } from "@/test/support/handlers/accounts"
import { searchTransactions } from "@/test/support/handlers/transactions"
import { renderWithProviders } from "@/test/support/render"
import { server } from "@/test/support/server"
import { Omnibox } from "@/components/layout/Omnibox"

const mainAccount = { ...makeAccount({ id: 7, name: "Compte joint" }), active: true, is_main: true }

function renderOmnibox() {
  server.use(listAccounts([mainAccount]), searchTransactions())
  return renderWithProviders(<Omnibox />, { route: "/", auth: true })
}

describe("Omnibox en anglais", () => {
  afterEach(() => setLanguage("fr"))

  it("traduit le champ, les destinations et les actions", async () => {
    await setLanguage("en")
    const { user } = renderOmnibox()
    await user.keyboard("{Meta>}k{/Meta}")

    expect(await screen.findByPlaceholderText("Search, or type “12.50 bakery”…")).toBeInTheDocument()
    expect(screen.getByRole("dialog", { name: "Search" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /Dashboard/ })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /Yearly review/ })).toBeInTheDocument()
    expect(await screen.findByRole("button", { name: /^New transaction\s*Compte joint/ })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /Import a CSV statement/ })).toBeInTheDocument()
  })

  it("filtre les destinations sur le libellé affiché", async () => {
    await setLanguage("en")
    const { user } = renderOmnibox()
    await user.keyboard("{Meta>}k{/Meta}")
    await user.type(await screen.findByPlaceholderText(/Search, or type/), "taxes")

    expect(await screen.findByRole("button", { name: /Taxes/ })).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: /Dashboard/ })).not.toBeInTheDocument()
  })

  it("saisie rapide : « 12.50 bakery » propose une dépense au format anglais", async () => {
    await setLanguage("en")
    const { user } = renderOmnibox()
    await user.keyboard("{Meta>}k{/Meta}")
    await user.type(await screen.findByPlaceholderText(/Search, or type/), "12,50 bakery")

    expect(await screen.findByRole("button", { name: /^Add an expense of €12\.50/ })).toBeInTheDocument()
  })
})
