import { Button } from "@/components/ui/button"
import { Table } from "@/components/ui/table"
import type { AccountDetailView } from "./useAccountDetail"
import { TransactionsToolbar } from "./TransactionsToolbar"
import { TransactionsMobileList } from "./TransactionsMobileList"
import { TransactionsTable } from "./TransactionsTable"

/** Section des transactions d'un compte courant ou d'épargne. */
export function TransactionsSection({ ctx }: { ctx: AccountDetailView }) {
  const { hasMoreTx, isInvestment, loadMoreTransactions, loadingMoreTx, transactions } = ctx
  return (
    <>
      {/* Transactions Table Section */}
      {!isInvestment && (
        <div className="space-y-4">
          <TransactionsToolbar ctx={ctx} />

          <TransactionsMobileList ctx={ctx} />

          <TransactionsTable ctx={ctx} />
          {hasMoreTx && (
            <div className="flex justify-center md:hidden">
              <Button variant="outline" className="h-11 w-full" onClick={loadMoreTransactions} disabled={loadingMoreTx}>
                {loadingMoreTx ? "Chargement…" : "Charger plus de transactions"}
              </Button>
            </div>
          )}
        </div>
      )}
    </>
  )
}
