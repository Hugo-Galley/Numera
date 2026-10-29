import { Archive, ArchiveRestore, Landmark } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { ImportDialog } from "@/components/import/ImportDialog"
import { Link } from "react-router-dom"
import { LoanDialog } from "@/components/loans/LoanDialog"
import { useAccounts } from "./useAccounts"
import { CreateAccountDialog } from "./CreateAccountDialog"
import { EditAccountDialog } from "./EditAccountDialog"
import { AccountsList } from "./AccountsList"

export default function Accounts() {
  const ctx = useAccounts()
  const { accounts, archivedAccounts, editingLoan, handleRestoreAccount, importOpen, loadAccounts, loanDialogOpen, setEditingLoan, setImportOpen, setLoanDialogOpen, setShowArchived, showArchived } = ctx
  return (
    <div className="space-y-8">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">Comptes</h1>
          <p className="text-muted-foreground">Gérez vos différents comptes bancaires et d'investissement.</p>
        </div>
        <div className="flex flex-col gap-2 sm:flex-row">
        <Button variant="outline" className="w-full sm:w-auto" onClick={() => { setEditingLoan(null); setLoanDialogOpen(true) }}>
          <Landmark className="mr-2 h-4 w-4" /> Ajouter un crédit
        </Button>
        <LoanDialog open={loanDialogOpen} onOpenChange={setLoanDialogOpen} loan={editingLoan} onSaved={() => loadAccounts()} />
        <CreateAccountDialog ctx={ctx} />
        </div>
      </div>

      {/* Edit Dialog */}
      <EditAccountDialog ctx={ctx} />

      <AccountsList ctx={ctx} />

      {archivedAccounts.length > 0 && (
        <div className="space-y-3">
          <Button variant="ghost" size="sm" className="text-slate-500" onClick={() => setShowArchived((v) => !v)}>
            <Archive className="mr-2 h-4 w-4" />
            {showArchived ? "Masquer les comptes archivés" : `Comptes archivés (${archivedAccounts.length})`}
          </Button>
          {showArchived && (
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {archivedAccounts.map((account) => (
                <Card key={account.id} className="shadow-sm opacity-75">
                  <CardContent className="flex items-center justify-between gap-3 p-4">
                    <div className="min-w-0">
                      <p className="truncate font-semibold text-slate-900">{account.name}</p>
                      <p className="text-xs text-slate-500">{account.institution || account.type} · {account.currency}</p>
                    </div>
                    <div className="flex shrink-0 gap-1">
                      <Button variant="ghost" size="sm" className="h-10 md:h-8" asChild>
                        <Link to={`/accounts/${account.id}`}>Historique</Link>
                      </Button>
                      <Button variant="outline" size="sm" className="h-10 md:h-8" onClick={() => handleRestoreAccount(account.id)}>
                        <ArchiveRestore className="mr-1 h-4 w-4" />
                        Réactiver
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>
      )}

      <ImportDialog open={importOpen} onOpenChange={setImportOpen} onImported={loadAccounts} />
    </div>
  )
}
