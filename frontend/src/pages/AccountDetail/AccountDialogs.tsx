import { ImportDialog } from "@/components/import/ImportDialog"
import { ReconcileDialog } from "@/components/accounts/ReconcileDialog"
import { ReimbursementDialog } from "@/components/reimbursements/ReimbursementDialog"
import { SplitTransactionDialog } from "@/components/transactions/SplitTransactionDialog"
import { TransferLinkDialog } from "@/components/transfers/TransferLinkDialog"
import type { AccountDetailView } from "./useAccountDetail"

/** Dialogues partagés : remboursement, découpage, import, rapprochement, virement. */
export function AccountDialogs({ ctx }: { ctx: AccountDetailView }) {
  const { account, allAccounts, categories, id, importOpen, loadData, loadTransactions, reconcileOpen, reimbursementTx, setImportOpen, setReconcileOpen, setReimbursementTx, setSplitTx, setTransferTx, splitTx, transferTx } = ctx
  return (
    <>
      <ReimbursementDialog
        open={reimbursementTx !== null}
        onOpenChange={(o) => !o && setReimbursementTx(null)}
        transaction={reimbursementTx}
        onDone={loadTransactions}
      />

      <SplitTransactionDialog
        open={splitTx !== null}
        onOpenChange={(o) => !o && setSplitTx(null)}
        transaction={splitTx}
        categories={categories}
        onDone={loadTransactions}
      />

      <ImportDialog
        open={importOpen}
        onOpenChange={setImportOpen}
        accountId={account.id}
        onImported={() => loadData({ quiet: true })}
      />
      <ReconcileDialog
        account={account}
        open={reconcileOpen}
        onOpenChange={setReconcileOpen}
        onVerified={() => loadData({ quiet: true })}
      />
      <TransferLinkDialog
        open={transferTx !== null}
        onOpenChange={(o) => !o && setTransferTx(null)}
        transaction={transferTx}
        accounts={allAccounts}
        onDone={() => {
          setTransferTx(null)
          loadTransactions()
        }}
      />
    </>
  )
}
