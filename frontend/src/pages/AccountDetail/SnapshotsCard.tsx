import { ArrowDown, ArrowUp, Pencil, Trash2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { format } from "date-fns"
import { useTranslation } from "react-i18next"
import type { AccountDetailView } from "./useAccountDetail"

/** Derniers snapshots de valorisation. */
export function SnapshotsCard({ ctx }: { ctx: AccountDetailView }) {
  const { t } = useTranslation("accountDetail")
  const { t: tc } = useTranslation("common")
  const { formatCurrency, handleDeleteSnapshot, handleEditSnapshot, handleSnapSort, snapSortField, snapSortOrder, sortedSnapshots } = ctx
  return (
    <>
      <Card className="min-w-0 shadow-sm">
        <CardHeader><CardTitle className="text-lg">{t("snapshots.title")}</CardTitle></CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
              <TableRow>
                <TableHead className="cursor-pointer hover:bg-slate-100 transition-colors" onClick={() => handleSnapSort("date")}>
                  <div className="flex items-center gap-2">
                    {t("snapshots.date")}
                    {snapSortField === "date" && (snapSortOrder === "asc" ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />)}
                  </div>
                </TableHead>
                <TableHead className="text-right cursor-pointer hover:bg-slate-100 transition-colors" onClick={() => handleSnapSort("current_value")}>
                  <div className="flex items-center justify-end gap-2">
                    {t("snapshots.value")}
                    {snapSortField === "current_value" && (snapSortOrder === "asc" ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />)}
                  </div>
                </TableHead>
                <TableHead className="text-right w-[80px]">{tc("actions.actions")}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {sortedSnapshots.map((snap) => (
                <TableRow key={snap.id}>
                  <TableCell className="text-xs">{format(new Date(snap.date), "dd/MM/yyyy")}</TableCell>
                  <TableCell className="text-right font-bold">
                    <span className="amount-blur">{formatCurrency(snap.current_value)}</span>
                  </TableCell>
                  <TableCell className="text-right">
                     <div className="flex items-center justify-end gap-1">
                       <Button aria-label={tc("actions.edit")} variant="ghost" size="sm" onClick={() => handleEditSnapshot(snap)} className="h-8 w-8 p-0"><Pencil className="h-3 w-3" /></Button>
                       <Button aria-label={tc("actions.delete")} variant="ghost" size="sm" onClick={() => handleDeleteSnapshot(snap.id)} className="h-8 w-8 p-0 text-rose-500"><Trash2 className="h-3 w-3" /></Button>
                     </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
       </div>
        </CardContent>
      </Card>
    </>
  )
}
