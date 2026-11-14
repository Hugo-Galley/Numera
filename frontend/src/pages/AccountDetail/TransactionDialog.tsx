import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { Plus } from "lucide-react"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { useTranslation } from "react-i18next"
import type { AccountDetailView } from "./useAccountDetail"

/** Dialogue de création / modification d'une transaction (comptes hors investissement). */
export function TransactionDialog({ ctx }: { ctx: AccountDetailView }) {
  const { t } = useTranslation("accountDetail")
  const { t: tc } = useTranslation("common")
  const { availableTags, categories, editTxId, handleCreateTransaction, handleCreateTransactionBusy, handleUpdateTransaction, handleUpdateTransactionBusy, knownMerchants, resetTxForm, setTxAmount, setTxCategoryId, setTxCurrency, setTxCustomColor, setTxCustomIcon, setTxDate, setTxIsExceptional, setTxIsRecurring, setTxMerchant, setTxOpen, setTxTagIds, setTxType, txAmount, txCategoryId, txCurrency, txCustomColor, txCustomIcon, txDate, txIsExceptional, txIsRecurring, txMerchant, txOpen, txTagIds, txType } = ctx
  return (
    <>
      <Dialog open={txOpen} onOpenChange={(open) => { if (!open) { setTxOpen(false); resetTxForm(); } else { setTxOpen(true); } }}>
        <DialogTrigger asChild>
          <Button className="h-11 w-full bg-slate-900 text-white shadow-md hover:bg-slate-800 sm:h-10 sm:w-auto">
            <Plus className="h-4 w-4 mr-2" /> {t("tx.dialog.new")}
          </Button>
        </DialogTrigger>
        <DialogContent className="max-sm:[&_input]:text-base sm:max-w-[425px] rounded-2xl border-none shadow-2xl max-h-[calc(100dvh-2*max(1rem,env(safe-area-inset-top)))] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="text-2xl font-bold">{editTxId ? t("tx.dialog.edit") : t("tx.dialog.new")}</DialogTitle>
            <DialogDescription>
              {editTxId ? t("tx.dialog.editHint") : t("tx.dialog.newHint")}
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-5 py-4 sm:gap-6 sm:py-6">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div className="grid gap-2">
                <Label htmlFor="date" className="text-xs uppercase tracking-wider font-bold text-slate-500">{t("tx.dialog.date")}</Label>
                <Input id="date" type="datetime-local" value={txDate} onChange={(e) => setTxDate(e.target.value)} className="bg-slate-50 border-slate-200" />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="type" className="text-xs uppercase tracking-wider font-bold text-slate-500">{t("tx.dialog.flow")}</Label>
                <Select value={txType} onValueChange={setTxType}>
                  <SelectTrigger id="type" className="bg-slate-50 border-slate-200"><SelectValue placeholder={t("tx.type")} /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="Entree">{t("tx.dialog.incomePlus")}</SelectItem>
                    <SelectItem value="Sortie">{t("tx.dialog.expenseMinus")}</SelectItem>
                    <SelectItem value="Solde Initial">{tc("txTypes.initial")}</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="grid gap-2">
              <Label htmlFor="merchant" className="text-xs uppercase tracking-wider font-bold text-slate-500">{t("tx.dialog.merchant")}</Label>
              <Input 
                id="merchant" 
                list="merchant-list" 
                autoComplete="off"
                value={txMerchant} 
                onChange={(e) => setTxMerchant(e.target.value)} 
                placeholder={t("tx.dialog.merchantPlaceholder")} 
                className="bg-slate-50 border-slate-200" 
              />
              <datalist id="merchant-list">
                {knownMerchants.map((m, idx) => (
                  <option key={idx} value={m} />
                ))}
              </datalist>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="grid gap-2">
                <Label htmlFor="amount" className="text-xs uppercase tracking-wider font-bold text-slate-500">{t("tx.dialog.amount")}</Label>
                <Input id="amount" type="number" inputMode="decimal" min={0.01} step="0.01" value={txAmount} onChange={(e) => setTxAmount(e.target.value)} placeholder="0.00" className="bg-slate-50 border-slate-200 font-bold" />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="currency" className="text-xs uppercase tracking-wider font-bold text-slate-500">{t("tx.dialog.currency")}</Label>
                <Select value={txCurrency} onValueChange={setTxCurrency}>
                  <SelectTrigger id="currency" className="bg-slate-50 border-slate-200"><SelectValue placeholder={t("tx.dialog.currency")} /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="EUR">EUR (€)</SelectItem>
                    <SelectItem value="USD">USD ($)</SelectItem>
                    <SelectItem value="GBP">GBP (£)</SelectItem>
                    <SelectItem value="CHF">CHF (CHF)</SelectItem>
                    <SelectItem value="JPY">JPY (¥)</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="grid gap-2">
              <Label htmlFor="category" className="text-xs uppercase tracking-wider font-bold text-slate-500">{t("tx.dialog.categoryField")}</Label>
              <Select value={txCategoryId} onValueChange={setTxCategoryId}>
                <SelectTrigger id="category" className="bg-slate-50 border-slate-200"><SelectValue placeholder={t("tx.dialog.choose")} /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">{tc("actions.none")}</SelectItem>
                  {categories.filter((cat) => !cat.archived || String(cat.id) === txCategoryId).map((cat) => <SelectItem key={cat.id} value={String(cat.id)}>{cat.name}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>

            {availableTags.length > 0 && (
              <div className="grid gap-2">
                <Label className="text-xs uppercase tracking-wider font-bold text-slate-500">{t("tx.dialog.tags")}</Label>
                <div className="flex flex-wrap gap-2 p-3 bg-slate-50 rounded-xl border border-slate-200">
                  {availableTags.filter((tag) => !tag.archived || txTagIds.includes(tag.id)).map((tag) => (
                    <div key={tag.id} className="flex items-center space-x-2">
                      <Checkbox 
                        id={`tag-${tag.id}`} 
                        checked={txTagIds.includes(tag.id)}
                        onCheckedChange={(checked) => {
                          if (checked) {
                            setTxTagIds([...txTagIds, tag.id])
                          } else {
                            setTxTagIds(txTagIds.filter(tid => tid !== tag.id))
                          }
                        }}
                      />
                      <label
                        htmlFor={`tag-${tag.id}`}
                        className="text-xs font-medium leading-none cursor-pointer"
                      >
                        <Badge 
                          variant="outline" 
                          className="px-2 py-0 h-5 border-none text-white font-bold text-[9px]"
                          style={{ backgroundColor: tag.color || "#64748b" }}
                        >
                          {tag.name}
                        </Badge>
                      </label>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="flex items-center space-x-2 py-2">
              <Checkbox id="recurring" checked={txIsRecurring} onCheckedChange={(checked) => setTxIsRecurring(!!checked)} />
              <Label htmlFor="recurring" className="text-sm font-medium leading-none cursor-pointer">{t("tx.dialog.recurring")}</Label>
            </div>

            {txType === "Sortie" && (
              <div className="flex items-center space-x-2 py-2">
                <Checkbox id="exceptional" checked={txIsExceptional} onCheckedChange={(checked) => setTxIsExceptional(!!checked)} />
                <Label htmlFor="exceptional" className="text-sm font-medium leading-none cursor-pointer">{t("tx.dialog.exceptional")}</Label>
              </div>
            )}

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div className="grid gap-2">
                <Label htmlFor="custom_icon" className="text-xs uppercase tracking-wider font-bold text-slate-500">{t("tx.dialog.icon")}</Label>
                <Input id="custom_icon" value={txCustomIcon} onChange={(e) => setTxCustomIcon(e.target.value)} placeholder={t("tx.dialog.iconPlaceholder")} className="bg-slate-50 border-slate-200" />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="custom_color" className="text-xs uppercase tracking-wider font-bold text-slate-500">{t("tx.dialog.color")}</Label>
                <div className="flex gap-2">
                  <Input id="custom_color" type="color" value={txCustomColor} onChange={(e) => setTxCustomColor(e.target.value)} className="w-12 p-1 h-10 bg-slate-50 border-slate-200 cursor-pointer" />
                  <Input value={txCustomColor} onChange={(e) => setTxCustomColor(e.target.value)} className="flex-1 bg-slate-50 border-slate-200" />
                </div>
              </div>
            </div>
          </div>
          <DialogFooter><Button variant="ghost" onClick={() => { setTxOpen(false); resetTxForm(); }}>{tc("actions.cancel")}</Button><Button onClick={editTxId ? () => handleUpdateTransaction() : () => handleCreateTransaction()} disabled={handleCreateTransactionBusy || handleUpdateTransactionBusy} className="bg-slate-900 text-white shadow-lg">{handleCreateTransactionBusy || handleUpdateTransactionBusy ? tc("actions.saving") : tc("actions.save")}</Button></DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}
