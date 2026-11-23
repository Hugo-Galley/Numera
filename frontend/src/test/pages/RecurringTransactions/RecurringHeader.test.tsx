/** En-tête d'Échéances : le choix « Analyse / Liste » et la génération ne s'affichent que sur l'onglet Récurrences. */
import { screen } from "@testing-library/react"
import { partial } from "@/test/support/factories"
import { renderWithProviders } from "@/test/support/render"
import { RecurringHeader } from "@/pages/RecurringTransactions/RecurringHeader"
import type { RecurringTransactionsCtx } from "@/pages/RecurringTransactions/useRecurringTransactions"

const ctx = (activeTab: string) =>
  partial<RecurringTransactionsCtx>({
    activeTab,
    recurringView: "analysis",
    changeRecurringView: vi.fn(),
    handleOpenCreate: vi.fn(),
    handleTrigger: vi.fn(),
    handleTriggerBusy: false,
  })

describe("RecurringHeader", () => {
  it.each(["subscriptions", "recurring"])("onglet Récurrences (%s) : vue Analyse / Liste et génération proposées", (tab) => {
    renderWithProviders(<RecurringHeader ctx={ctx(tab)} />)

    expect(screen.getByRole("group", { name: "Vue des récurrences" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Lancer la génération" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Nouvelle récurrence" })).toBeInTheDocument()
  })

  it.each(["calendar", "salary"])("onglet %s : ni sélecteur de vue ni génération, la création reste", (tab) => {
    renderWithProviders(<RecurringHeader ctx={ctx(tab)} />)

    expect(screen.queryByRole("group", { name: "Vue des récurrences" })).not.toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "Lancer la génération" })).not.toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Nouvelle récurrence" })).toBeInTheDocument()
  })
})
