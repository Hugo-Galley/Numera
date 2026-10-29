import { ArrowDown, ArrowRightLeft, ArrowUp, HandCoins, Repeat, Split } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Checkbox } from "@/components/ui/checkbox"
import { CompanyLogo } from "@/components/ui/CompanyLogo"
import { IconComponent } from "@/components/dashboard/IconComponent"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { format } from "date-fns"
import type { AccountDetailView } from "./useAccountDetail"

/** Tableau des transactions (bureau). */
export function TransactionsTable({ ctx }: { ctx: AccountDetailView }) {
  const { account, filteredTransactions, formatCurrency, formatValue, handleSort, hasMoreTx, id, loadMoreTransactions, loadingMoreTx, renderTxMenu, selectedIds, setSelectedIds, sortField, sortOrder, transactions, txLoading } = ctx
  return (
    <>
      <Card className={`hidden shadow-sm border-slate-100 overflow-hidden md:block transition-opacity ${txLoading ? "opacity-50" : ""}`}>
        <div className="overflow-x-auto">
          <Table>
            <TableHeader className="bg-slate-50/50">
          <TableRow>
            <TableHead className="w-[50px]">
              <Checkbox 
                checked={selectedIds.length === filteredTransactions.length && filteredTransactions.length > 0}
                onCheckedChange={(checked) => {
                  if (checked) {
                    setSelectedIds(filteredTransactions.map(t => t.id))
                  } else {
                    setSelectedIds([])
                  }
                }}
              />
            </TableHead>
            <TableHead className="w-[150px] cursor-pointer hover:bg-slate-100 transition-colors" onClick={() => handleSort("date")}>
              <div className="flex items-center gap-2">
                Date
                {sortField === "date" && (sortOrder === "asc" ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />)}
              </div>
            </TableHead>
            <TableHead className="cursor-pointer hover:bg-slate-100 transition-colors" onClick={() => handleSort("merchant")}>
              <div className="flex items-center gap-2">
                Commerçant
                {sortField === "merchant" && (sortOrder === "asc" ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />)}
              </div>
            </TableHead>
            <TableHead className="cursor-pointer hover:bg-slate-100 transition-colors" onClick={() => handleSort("category")}>
              <div className="flex items-center gap-2">
                Catégorie / Type
                {sortField === "category" && (sortOrder === "asc" ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />)}
              </div>
            </TableHead>
            <TableHead className="text-right cursor-pointer hover:bg-slate-100 transition-colors" onClick={() => handleSort("amount")}>
              <div className="flex items-center justify-end gap-2">
                Montant
                {sortField === "amount" && (sortOrder === "asc" ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />)}
              </div>
            </TableHead>
            <TableHead className="text-right cursor-pointer hover:bg-slate-100 transition-colors" onClick={() => handleSort("running_balance")}>
              <div className="flex items-center justify-end gap-2">
                Solde
                {sortField === "running_balance" && (sortOrder === "asc" ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />)}
              </div>
            </TableHead>
            <TableHead className="text-right w-[100px]">Actions</TableHead>
          </TableRow>
        </TableHeader>
          <TableBody>
            {filteredTransactions.map((tx) => (
              <TableRow key={tx.id}>
                <TableCell>
                  <Checkbox 
                    checked={selectedIds.includes(tx.id)}
                    onCheckedChange={(checked) => {
                      if (checked) {
                        setSelectedIds(prev => [...prev, tx.id])
                      } else {
                        setSelectedIds(prev => prev.filter(id => id !== tx.id))
                      }
                    }}
                  />
                </TableCell>
                <TableCell className="text-xs">{format(new Date(tx.date), "dd/MM/yyyy")}</TableCell>
                <TableCell title={tx.merchant}>
                  <div className="flex items-center gap-2.5">
                  {tx.recurring_logo && (
                    <CompanyLogo logo={tx.recurring_logo} name={tx.merchant} className="h-7 w-7 rounded-md" />
                  )}
                  <div className="flex flex-col">
                    <div className="flex items-center gap-1.5">
                      {tx.merchant_obj && (
                        <div className="h-2 w-2 rounded-full shrink-0" style={{ backgroundColor: tx.merchant_obj.color || "#64748b" }} />
                      )}
                      <span className="font-bold text-slate-900">{tx.merchant_obj?.name || tx.merchant}</span>
                      {tx.is_recurring && <Repeat className="h-3 w-3 text-indigo-500" />}
                    </div>
                    {tx.note && <span className="text-[10px] text-slate-400 truncate max-w-[200px]">{tx.note}</span>}
                    {tx.merchant_obj && tx.merchant_obj.name !== tx.merchant && (
                       <span className="text-[9px] text-slate-400 italic truncate max-w-[180px]">{tx.merchant}</span>
                    )}
                    {tx.tags && tx.tags.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-1">
                        {tx.tags.map(tag => (
                          <Badge 
                            key={tag.id} 
                            className="px-1.5 py-0 text-[8px] font-bold border-none text-white"
                            style={{ backgroundColor: tag.color || "#64748b" }}
                          >
                            {tag.name}
                          </Badge>
                        ))}
                      </div>
                    )}
                  </div>
                  </div>
                </TableCell>
                <TableCell>
                  {tx.type === "Solde Initial" ? (
                    <Badge variant="outline" className="bg-slate-100 text-slate-600 border-none">Solde Initial</Badge>
                  ) : tx.type === "Interets" ? (
                    <Badge variant="outline" className="bg-amber-50 text-amber-700 border-none">Intérêts</Badge>
                  ) : (
                    <div className="flex items-center gap-2">
                      <div className="h-6 w-6 rounded-md flex items-center justify-center" style={{ backgroundColor: tx.category?.color || "#f1f5f9" }}>
                        <IconComponent name={tx.category?.icon} className="h-3.5 w-3.5 text-white" />
                      </div>
                      <span className="text-sm font-medium text-slate-600" title={tx.splits?.length ? tx.splits.map((p: any) => `${p.category?.name ?? "?"} : ${formatCurrency(p.amount)}`).join("\n") : undefined}>
                        {tx.category?.name || "Sans catégorie"}
                        {tx.splits?.length ? <span className="ml-1 inline-flex items-center gap-0.5 text-xs text-slate-400"><Split className="h-3 w-3" />+{tx.splits.length - 1}</span> : null}
                      </span>
                    </div>
                  )}
                </TableCell>
                <TableCell className={`text-right font-bold ${tx.type === "Sortie" ? "text-rose-600" : (tx.type === "Entree" || tx.type === "Interets") ? "text-emerald-600" : "text-slate-900"}`}>
                  <div className="flex flex-col items-end">
                    <span className="amount-blur">
                      {tx.type === "Sortie" ? "-" : (tx.type === "Entree" || tx.type === "Interets") ? "+" : ""}{formatCurrency(tx.amount)}
                    </span>
                    {(tx.reimbursement_offset ?? 0) > 0 && (
                      <span className="text-[10px] font-normal text-slate-400 amount-blur">
                        net {formatCurrency(tx.amount - (tx.reimbursement_offset ?? 0))}
                      </span>
                    )}
                    {tx.type === "Sortie" && tx.has_claims && (() => {
                      const received = tx.reimbursement_offset ?? 0
                      const expected = tx.reimbursement_expected ?? 0
                      const [label, tone] = received <= 0
                        ? ["À rembourser", "bg-amber-50 text-amber-700"]
                        : received < expected - 0.005
                          ? ["Partiel", "bg-sky-50 text-sky-700"]
                          : ["Remboursé", "bg-emerald-50 text-emerald-700"]
                      return <Badge variant="outline" className={`mt-0.5 border-none px-1 py-0 text-[10px] ${tone}`}>{label}</Badge>
                    })()}
                    {tx.currency !== account.currency && (
                      <span className="text-[10px] text-slate-400 font-normal amount-blur">
                        ({formatValue(tx.original_amount, tx.currency)})
                      </span>
                    )}
                  </div>
                </TableCell>
                <TableCell className="text-right font-extrabold">
                  <span className="amount-blur">{formatCurrency(tx.running_balance)}</span>
                </TableCell>
                <TableCell className="text-right">
                  <div className="flex items-center justify-end gap-1">
                    {/* Seuls les liens actifs restent visibles ; les actions sont dans le menu */}
                    {(tx.has_claims || (tx.reimbursement_offset ?? 0) > 0) && (
                      <span title="Remboursement lié" className="flex h-8 w-6 items-center justify-center">
                        <HandCoins className="h-3.5 w-3.5 text-emerald-600" />
                      </span>
                    )}
                    {tx.is_transfer && (
                      <span title="Virement interne lié" className="flex h-8 w-6 items-center justify-center">
                        <ArrowRightLeft className="h-3.5 w-3.5 text-emerald-600" />
                      </span>
                    )}
                    {renderTxMenu(tx)}
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
        </div>
        {hasMoreTx && (
          <div className="hidden justify-center border-t p-3 md:flex">
            <Button variant="outline" size="sm" onClick={loadMoreTransactions} disabled={loadingMoreTx}>
              {loadingMoreTx ? "Chargement…" : "Charger plus de transactions"}
            </Button>
          </div>
        )}
      </Card>
    </>
  )
}
