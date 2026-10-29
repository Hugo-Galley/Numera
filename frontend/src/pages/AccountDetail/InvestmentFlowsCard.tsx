import { ArrowDown, ArrowUp, Pencil, Trash2 } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { format } from "date-fns"
import { Transaction } from "./types"
import type { AccountDetailView } from "./useAccountDetail"

/** Historique des flux d'un compte d'investissement. */
export function InvestmentFlowsCard({ ctx }: { ctx: AccountDetailView }) {
  const { account, formatCurrency, formatValue, handleDeleteInvTransaction, handleDeleteTransaction, handleEditInvTransaction, handleInvSort, id, invSortField, invSortOrder, investmentData, sortedInvestmentTransactions, transactions } = ctx
  return (
    <>
      <Card className="min-w-0 shadow-sm">
        <CardHeader><CardTitle className="text-lg">Historique des flux</CardTitle></CardHeader>
        <CardContent className="p-0">
          <div className="divide-y md:hidden">
            {sortedInvestmentTransactions.map((tx: any) => (
              <div key={tx.id + (tx.is_regular ? "-reg" : "-inv")} className="flex items-start gap-1 py-2 pl-4 pr-2">
                <div className="min-w-0 flex-1 py-1">
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1">
                      <Badge variant="outline" className="h-5 w-fit py-0 text-[10px] capitalize">{tx.type}</Badge>
                      <span className="break-words text-sm font-bold text-slate-900">{tx.note || tx.ticker || "Transaction"}</span>
                    </div>
                    <span className="shrink-0 whitespace-nowrap text-sm font-bold tabular-nums amount-blur">{formatCurrency(tx.amount)}</span>
                  </div>
                  <div className="mt-1 flex flex-wrap items-center gap-x-1.5 text-xs text-slate-500">
                    <span>{format(new Date(tx.date), "dd/MM/yy")}</span>
                    {tx.ticker && <span className="font-mono text-slate-400">· {tx.ticker}</span>}
                    {tx.quantity != null && <span className="text-slate-400">· {tx.quantity} part{tx.quantity > 1 ? "s" : ""}</span>}
                    {tx.unit_price != null && <span className="text-slate-400 amount-blur">@ {formatCurrency(tx.unit_price)}</span>}
                    {tx.reinvested && <span className="text-emerald-600">· réinvesti</span>}
                    {tx.reinvest_of_id && <span className="text-emerald-600">↳ dividende réinvesti</span>}
                    {tx.currency && tx.currency !== account.currency && (
                      <span className="text-slate-400 amount-blur">({formatValue(tx.original_amount || tx.amount, tx.currency)})</span>
                    )}
                  </div>
                </div>
                <div className="flex shrink-0 items-center">
                  {!tx.is_regular && (
                    <Button variant="ghost" size="icon" aria-label="Modifier" onClick={() => handleEditInvTransaction(tx)} className="h-10 w-10"><Pencil className="h-4 w-4" /></Button>
                  )}
                  <Button variant="ghost" size="icon" aria-label="Supprimer" onClick={() => tx.is_regular ? handleDeleteTransaction(tx.id) : handleDeleteInvTransaction(tx.id)} className="h-10 w-10 text-rose-500"><Trash2 className="h-4 w-4" /></Button>
                </div>
              </div>
            ))}
            {(investmentData?.transactions || []).length === 0 && (
              <p className="py-10 text-center text-slate-400">Aucun flux enregistré.</p>
            )}
          </div>
          <div className="hidden overflow-x-auto md:block">
            <Table>                 <TableHeader>
              <TableRow>
                <TableHead className="cursor-pointer hover:bg-slate-100 transition-colors" onClick={() => handleInvSort("date")}>
                  <div className="flex items-center gap-2">
                    Date
                    {invSortField === "date" && (invSortOrder === "asc" ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />)}
                  </div>
                </TableHead>
                <TableHead className="cursor-pointer hover:bg-slate-100 transition-colors" onClick={() => handleInvSort("type")}>
                  <div className="flex items-center gap-2">
                    Libellé / Type
                    {invSortField === "type" && (invSortOrder === "asc" ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />)}
                  </div>
                </TableHead>
                <TableHead className="text-right cursor-pointer hover:bg-slate-100 transition-colors" onClick={() => handleInvSort("amount")}>
                  <div className="flex items-center justify-end gap-2">
                    Montant
                    {invSortField === "amount" && (invSortOrder === "asc" ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />)}
                  </div>
                </TableHead>
                <TableHead className="text-right w-[80px]">Actions</TableHead>
              </TableRow>
            </TableHeader>
             <TableBody>
              {sortedInvestmentTransactions.map((tx: any) => (
                <TableRow key={tx.id + (tx.is_regular ? "-reg" : "-inv")}>
                  <TableCell className="text-xs">{format(new Date(tx.date), "dd/MM/yyyy")}</TableCell>
                  <TableCell>
                    <div className="flex flex-col gap-0.5">
                      <div className="flex items-center gap-2">
                        <Badge variant="outline" className="capitalize w-fit text-[10px] py-0 h-4">{tx.type}</Badge>
                        <span className="font-bold text-xs text-slate-900 line-clamp-1">{tx.note || tx.ticker || "Transaction"}</span>
                      </div>
                      {tx.ticker && (
                        <div className="flex items-center gap-1.5 text-[10px] text-slate-400 font-mono mt-0.5">
                          <span className="font-medium">{tx.ticker}</span>
                          {tx.quantity != null && (
                            <span>• {tx.quantity} part{tx.quantity > 1 ? "s" : ""}</span>
                          )}
                          {tx.unit_price != null && (
                            <span>@ {formatCurrency(tx.unit_price)}</span>
                          )}
                          {tx.withholding_tax ? (
                            <span>• retenue {formatValue(tx.withholding_tax, tx.currency || account.currency)}</span>
                          ) : null}
                          {tx.reinvested && <span className="text-emerald-600">• réinvesti</span>}
                          {tx.reinvest_of_id && <span className="text-emerald-600">↳ dividende réinvesti</span>}
                        </div>
                      )}
                    </div>
                  </TableCell>
                  <TableCell className="text-right font-bold">
                    <div className="flex flex-col items-end">
                      <span className="amount-blur">{formatCurrency(tx.amount)}</span>
                      {tx.currency && tx.currency !== account.currency && (
                        <span className="text-[10px] text-slate-400 font-normal amount-blur">
                          ({formatValue(tx.original_amount || tx.amount, tx.currency)})
                        </span>
                      )}
                    </div>
                  </TableCell>
                  <TableCell className="text-right">
                     {tx.is_regular ? (
                       <div className="flex items-center justify-end gap-1">
                         <Button aria-label="Supprimer" variant="ghost" size="sm" onClick={() => handleDeleteTransaction(tx.id)} className="h-8 w-8 p-0 text-rose-500"><Trash2 className="h-3 w-3" /></Button>
                       </div>
                     ) : (
                       <div className="flex items-center justify-end gap-1">
                         <Button aria-label="Modifier" variant="ghost" size="sm" onClick={() => handleEditInvTransaction(tx)} className="h-8 w-8 p-0"><Pencil className="h-3 w-3" /></Button>
                         <Button aria-label="Supprimer" variant="ghost" size="sm" onClick={() => handleDeleteInvTransaction(tx.id)} className="h-8 w-8 p-0 text-rose-500"><Trash2 className="h-3 w-3" /></Button>
                       </div>
                     )}
                  </TableCell>
                </TableRow>
              ))}
              {(investmentData?.transactions || []).length === 0 && (
                <TableRow><TableCell colSpan={4} className="text-center py-10 text-slate-400">Aucun flux enregistré.</TableCell></TableRow>
              )}
            </TableBody>
          </Table>
       </div>
        </CardContent>
      </Card>
    </>
  )
}
