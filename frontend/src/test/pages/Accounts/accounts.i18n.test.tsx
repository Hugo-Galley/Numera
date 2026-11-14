/** Page Comptes, import et crédits : textes, pluriels et formats en français comme en anglais. */
import { screen, within } from "@testing-library/react"
import { http, HttpResponse } from "msw"
import { setLanguage } from "@/i18n"
import { accountTypeLabel, categoryTypeLabel } from "@/lib/labels"
import { formatMonths } from "@/components/loans/types"
import { LoanDialog } from "@/components/loans/LoanDialog"
import { makeAccount } from "@/test/support/factories"
import { listAccounts } from "@/test/support/handlers/accounts"
import { apiUrl } from "@/test/support/handlers"
import { renderWithProviders } from "@/test/support/render"
import { server } from "@/test/support/server"
import Accounts from "@/pages/Accounts/index"

const suggestions = http.get(apiUrl("/analytics/asset-allocation/suggestions"), () =>
  HttpResponse.json({ asset_classes: [], sectors: [], geographic_zones: [] }),
)

describe("page Comptes", () => {
  beforeEach(() => {
    server.use(
      suggestions,
      listAccounts([
        { ...makeAccount({ id: 1, name: "Livret perso", type: "epargne", balance: 1234.5 }), active: true },
        { ...makeAccount({ id: 2, name: "Ancien compte", type: "courant" }), active: false },
      ]),
    )
  })
  afterEach(() => setLanguage("fr"))

  it("en français", async () => {
    renderWithProviders(<Accounts />, { auth: true })
    expect((await screen.findAllByText("Livret perso")).length).toBeGreaterThan(0)
    expect(screen.getByRole("heading", { name: "Comptes" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /Ajouter un crédit/ })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Comptes archivés (1)" })).toBeInTheDocument()
  })

  it("en anglais : titres, colonnes, statut, type de compte et montant", async () => {
    await setLanguage("en")
    renderWithProviders(<Accounts />, { auth: true })
    expect((await screen.findAllByText("Livret perso")).length).toBeGreaterThan(0)
    expect(screen.getByRole("heading", { name: "Accounts" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /Add a loan/ })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /Add an account/ })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Archived accounts (1)" })).toBeInTheDocument()
    const table = screen.getByRole("table")
    for (const header of ["Name", "Institution", "Currency", "Balance", "Status", "Actions"]) {
      expect(within(table).getByRole("columnheader", { name: new RegExp(header) })).toBeInTheDocument()
    }
    expect(within(table).getByText("Savings")).toBeInTheDocument()
    expect(within(table).getByText("Active")).toBeInTheDocument()
    expect(within(table).getByText("€1,234.50")).toBeInTheDocument()
  })

  it("ouvre le dialogue de création en anglais", async () => {
    await setLanguage("en")
    const { user } = renderWithProviders(<Accounts />, { auth: true })
    await screen.findAllByText("Livret perso")
    await user.click(screen.getByRole("button", { name: /Add an account/ }))
    const dialog = await screen.findByRole("dialog")
    expect(within(dialog).getByText("New account")).toBeInTheDocument()
    expect(within(dialog).getByLabelText("Account name")).toHaveAttribute("placeholder", "E.g. Boursorama Checking")
    expect(within(dialog).getByRole("button", { name: "Create" })).toBeInTheDocument()
    expect(within(dialog).getByRole("button", { name: "Cancel" })).toBeInTheDocument()
  })
})

describe("libellés partagés et crédits", () => {
  afterEach(() => setLanguage("fr"))

  it("types de compte et de catégorie dans les deux langues", async () => {
    expect(accountTypeLabel("assurance_vie")).toBe("Assurance-Vie")
    expect(accountTypeLabel(null)).toBe("Autre")
    expect(categoryTypeLabel("depense")).toBe("Dépense")
    await setLanguage("en")
    expect(accountTypeLabel("assurance_vie")).toBe("Life Insurance")
    expect(accountTypeLabel("crypto")).toBe("Crypto")
    expect(accountTypeLabel(null)).toBe("Other")
    expect(categoryTypeLabel("depense")).toBe("Expense")
  })

  it("durées de prêt avec pluriels", async () => {
    expect(formatMonths(15)).toBe("1 an et 3 mois")
    expect(formatMonths(24)).toBe("2 ans")
    expect(formatMonths(1)).toBe("1 mois")
    await setLanguage("en")
    expect(formatMonths(15)).toBe("1 year and 3 months")
    expect(formatMonths(24)).toBe("2 years")
    expect(formatMonths(1)).toBe("1 month")
  })

  it("dialogue de crédit en anglais", async () => {
    await setLanguage("en")
    renderWithProviders(<LoanDialog open onOpenChange={() => {}} onSaved={() => {}} />)
    expect(await screen.findByText("New loan")).toBeInTheDocument()
    expect(screen.getByLabelText("Amount borrowed (€)")).toBeInTheDocument()
    expect(screen.getByLabelText("Annual nominal rate (%)")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Save" })).toBeInTheDocument()
  })
})
