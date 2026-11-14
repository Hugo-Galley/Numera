import { useTranslation } from "react-i18next"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Target } from "lucide-react"
import type { AccountDetailView } from "./useAccountDetail"

/** Dialogue de définition du point zéro. */
export function ZeroPointDialog({ ctx }: { ctx: AccountDetailView }) {
  const { t } = useTranslation("accountDetail")
  const { account, handleSetZeroPoint, handleSetZeroPointBusy, resetZeroForm, setZeroDate, setZeroNote, setZeroOpen, setZeroValue, zeroDate, zeroNote, zeroOpen, zeroValue } = ctx
  return (
    <>
      <Dialog open={zeroOpen} onOpenChange={(open) => { if (!open) { setZeroOpen(false); resetZeroForm(); } else { setZeroOpen(true); } }}>
        <DialogTrigger asChild>
          <Button variant="ghost" size="sm" className="text-slate-500 hover:text-slate-900">
            <Target className="h-4 w-4 mr-2" /> {t("zeroPointDialog.nouveauPointZero")}
          </Button>
        </DialogTrigger>
        <DialogContent className="max-sm:[&_input]:text-base sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle className="text-2xl font-bold text-rose-600">{t("zeroPointDialog.nouveauPointZero")}</DialogTitle>
            <DialogDescription>
              {t("zeroPointDialog.attentionDefinirUnNouveauPoint")}
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-5 py-4 sm:gap-6 sm:py-6">
            <div className="grid gap-2">
              <Label htmlFor="zdate" className="text-xs uppercase tracking-wider font-bold text-slate-500">{t("zeroPointDialog.dateDEffet")}</Label>
              <Input id="zdate" type="date" value={zeroDate} onChange={(e) => setZeroDate(e.target.value)} className="bg-slate-50 border-slate-200" />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="zval" className="text-xs uppercase tracking-wider font-bold text-slate-500">{t("zeroPointDialog.referenceValue", { currency: account?.currency || "EUR" })}</Label>
              <Input id="zval" type="number" inputMode="decimal" step="0.01" value={zeroValue} onChange={(e) => setZeroValue(e.target.value)} placeholder="0.00" className="bg-slate-50 border-slate-200 font-bold text-lg" />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="znote" className="text-xs uppercase tracking-wider font-bold text-slate-500">{t("zeroPointDialog.motifDuReset")}</Label>
              <Input id="znote" value={zeroNote} onChange={(e) => setZeroNote(e.target.value)} placeholder={t("zeroPointDialog.exDebutDeLAnnee")} className="bg-slate-50 border-slate-200" />
            </div>
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => { setZeroOpen(false); resetZeroForm(); }}>{t("zeroPointDialog.annuler")}</Button>
            <Button onClick={() => handleSetZeroPoint()} disabled={handleSetZeroPointBusy} className="bg-rose-600 text-white hover:bg-rose-700 shadow-lg">{handleSetZeroPointBusy ? t("zeroPointDialog.enregistrement") : t("zeroPointDialog.reinitialiserLaBase")}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}
