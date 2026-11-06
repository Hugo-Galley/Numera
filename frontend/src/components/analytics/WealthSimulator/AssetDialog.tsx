import { useTranslation } from "react-i18next"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { toast } from "sonner"
import type { WealthSimulatorCtx } from "./useWealthSimulator"

/** Dialogue de modification d'une classe d'actifs. */
export function AssetDialog({ ctx }: { ctx: WealthSimulatorCtx }) {
  const { t } = useTranslation("tools")
  const { editingAsset, setEditingAsset, updateAsset } = ctx
  return (
    <>
      {/* POPUP DE MODIFICATION D'UNE CLASSE D'ACTIFS */}
      {editingAsset && (
        <Dialog open={!!editingAsset} onOpenChange={(open) => { if (!open) setEditingAsset(null) }}>
          <DialogContent className="sm:max-w-[400px] bg-white border border-slate-200 shadow-xl rounded-lg">
            <DialogHeader>
              <DialogTitle className="text-sm font-bold text-slate-900">{t("assetDialog.modifierLActif")}</DialogTitle>
              <DialogDescription className="text-xs text-slate-500">
                {t("assetDialog.ajustezLesParametresDeRendement")}
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-4 py-3">
              <div className="space-y-1">
                <Label htmlFor="edit-name" className="text-xs font-semibold text-slate-700">{t("assetDialog.nomDeLActif")}</Label>
                <Input
                  id="edit-name"
                  value={editingAsset.name}
                  onChange={(e) => setEditingAsset({ ...editingAsset, name: e.target.value })}
                  className="h-11 md:h-9 text-base md:text-xs"
                  placeholder={t("assetDialog.exActionsEtfWorldAssurance")}
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-1">
                  <Label htmlFor="edit-return" className="text-xs font-semibold text-slate-700">{t("assetDialog.rendementMoyen")}</Label>
                  <Input
                    id="edit-return"
                    type="number" inputMode="decimal"
                    step="0.1"
                    value={editingAsset.expectedReturn}
                    onChange={(e) => setEditingAsset({ ...editingAsset, expectedReturn: Number(e.target.value) })}
                    className="h-11 md:h-9 text-base md:text-xs"
                  />
                </div>
                <div className="space-y-1">
                  <Label htmlFor="edit-volatility" className="text-xs font-semibold text-slate-700">{t("assetDialog.volatilite")}</Label>
                  <Input
                    id="edit-volatility"
                    type="number" inputMode="decimal"
                    step="0.5"
                    value={editingAsset.volatility}
                    onChange={(e) => setEditingAsset({ ...editingAsset, volatility: Number(e.target.value) })}
                    className="h-11 md:h-9 text-base md:text-xs"
                  />
                </div>
              </div>
            </div>

            <div className="flex justify-end gap-2 border-t border-slate-100 pt-4 mt-2">
              <button
                type="button"
                onClick={() => setEditingAsset(null)}
                className="border border-slate-200 rounded px-3 py-1.5 text-xs font-semibold hover:bg-slate-50 text-slate-705 h-11 md:h-9 transition-colors"
              >
                {t("assetDialog.annuler")}
              </button>
              <button
                type="button"
                onClick={() => {
                  updateAsset(editingAsset.id, {
                    name: editingAsset.name,
                    expectedReturn: editingAsset.expectedReturn,
                    volatility: editingAsset.volatility
                  })
                  setEditingAsset(null)
                  toast.success(t("assetDialog.actifMisAJour"))
                }}
                className="bg-indigo-600 text-white rounded px-4 py-1.5 text-xs font-semibold hover:bg-indigo-700 h-11 md:h-9 transition-colors"
              >
                {t("assetDialog.enregistrer")}
              </button>
            </div>
          </DialogContent>
        </Dialog>
      )}
    </>
  )
}
