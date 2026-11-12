import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { LogoPicker } from "@/components/ui/LogoPicker"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { useTranslation } from "react-i18next"
import { TAX_WRAPPERS, TaxWrapper } from "./types"
import type { AccountsCtx } from "./useAccounts"

/** Dialogue de modification d'un compte. */
export function EditAccountDialog({ ctx }: { ctx: AccountsCtx }) {
  const { t } = useTranslation("accounts")
  const { t: tc } = useTranslation("common")
  const { CURRENCIES, editingAccount, handleUpdateAccount, handleUpdateAccountBusy, isEditDialogOpen, setEditingAccount, setIsEditDialogOpen, suggestions } = ctx
  return (
    <>
      <Dialog open={isEditDialogOpen} onOpenChange={setIsEditDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t("form.editTitle")}</DialogTitle>
            <DialogDescription>
              {t("form.editSubtitle")}
            </DialogDescription>
          </DialogHeader>
          {editingAccount && (
            <div className="grid gap-4 py-4">
              <div className="grid gap-2">
                <Label htmlFor="edit-name">{t("form.name")}</Label>
                <Input 
                  id="edit-name" 
                  value={editingAccount.name}
                  onChange={(e) => setEditingAccount({...editingAccount, name: e.target.value})}
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="edit-institution">{t("form.institution")}</Label>
                <Input 
                  id="edit-institution" 
                  placeholder={t("form.institutionPlaceholder")} 
                  value={editingAccount.institution || ""}
                  onChange={(e) => setEditingAccount({...editingAccount, institution: e.target.value})}
                  list="edit-institutions-list"
                />
                <datalist id="edit-institutions-list">
                  <option value="Boursorama" />
                  <option value="Fortuneo" />
                  <option value="Société Générale" />
                  <option value="BRED" />
                  <option value="CIC" />
                  <option value="Crédit Agricole" />
                  <option value="LCL" />
                  <option value="La Banque Postale" />
                  <option value="Revolut" />
                  <option value="N26" />
                </datalist>
              </div>
              <div className="grid gap-2">
                <Label>{t("form.logo")}</Label>
                <LogoPicker
                  value={editingAccount.logo || null}
                  onChange={(logo) => setEditingAccount({...editingAccount, logo})}
                  suggestFor={editingAccount.institution || editingAccount.name}
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="edit-type">{t("form.type")}</Label>
                <Select 
                  value={editingAccount.type} 
                  onValueChange={(v) => setEditingAccount({...editingAccount, type: v as typeof editingAccount.type})}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="courant">{tc("accountTypes.courant")}</SelectItem>
                    <SelectItem value="epargne">{tc("accountTypes.epargne")}</SelectItem>
                    <SelectItem value="investissement">{tc("accountTypes.investissement")}</SelectItem>
                    <SelectItem value="assurance_vie">{tc("accountTypes.assurance_vie")}</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {editingAccount.type === "assurance_vie" && (
                <div className="grid grid-cols-1 gap-4 pt-2 border-t mt-2 sm:grid-cols-2">
                  <div className="grid gap-2">
                    <Label htmlFor="edit-fonds_euros_pct">{t("form.euroFunds")}</Label>
                    <Input 
                      id="edit-fonds_euros_pct" 
                      type="number" inputMode="decimal"
                      min="0"
                      max="100"
                      placeholder={t("form.example", { value: 60 })} 
                      value={editingAccount.fonds_euros_pct !== undefined && editingAccount.fonds_euros_pct !== null ? editingAccount.fonds_euros_pct : ""} 
                      onChange={(e) => {
                        const val = e.target.value;
                        const num = val === "" ? 0 : parseFloat(val);
                        const otherNum = isNaN(num) ? 0 : Math.max(0, Math.min(100, 100 - num));
                        setEditingAccount({
                          ...editingAccount,
                          fonds_euros_pct: isNaN(num) ? undefined : num,
                          fonds_investis_pct: otherNum
                        });
                      }} 
                    />
                  </div>
                  <div className="grid gap-2">
                    <Label htmlFor="edit-fonds_investis_pct">{t("form.investedFunds")}</Label>
                    <Input 
                      id="edit-fonds_investis_pct" 
                      type="number" inputMode="decimal"
                      min="0"
                      max="100"
                      placeholder={t("form.example", { value: 40 })} 
                      value={editingAccount.fonds_investis_pct !== undefined && editingAccount.fonds_investis_pct !== null ? editingAccount.fonds_investis_pct : ""} 
                      onChange={(e) => {
                        const val = e.target.value;
                        const num = val === "" ? 0 : parseFloat(val);
                        const otherNum = isNaN(num) ? 0 : Math.max(0, Math.min(100, 100 - num));
                        setEditingAccount({
                          ...editingAccount,
                          fonds_investis_pct: isNaN(num) ? undefined : num,
                          fonds_euros_pct: otherNum
                        });
                      }} 
                    />
                  </div>
                </div>
              )}
              <div className="grid gap-2">
                <Label htmlFor="edit-currency">{t("form.currency")}</Label>
                <Select 
                  value={editingAccount.currency} 
                  onValueChange={(v) => setEditingAccount({...editingAccount, currency: v})}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {CURRENCIES.map(c => (
                      <SelectItem key={c} value={c}>{c}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {(editingAccount.type === "investissement" || editingAccount.type === "assurance_vie") && (
                <div className="grid gap-2 pt-2 border-t mt-2">
                  <Label htmlFor="edit-valuation_mode">{t("form.valuation")}</Label>
                  <Select value={editingAccount.valuation_mode ?? (editingAccount.type === "assurance_vie" ? "snapshot" : "positions")} onValueChange={(v) => setEditingAccount({...editingAccount, valuation_mode: v as "positions" | "snapshot"})}>
                    <SelectTrigger id="edit-valuation_mode">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="positions">{t("form.valuationPositions")}</SelectItem>
                      <SelectItem value="snapshot">{t("form.valuationSnapshot")}</SelectItem>
                    </SelectContent>
                  </Select>
                  <p className="text-xs text-slate-500">
                    {t("form.valuationHint")}
                  </p>
                </div>
              )}

              {editingAccount.type !== "courant" && (
                <div className="grid gap-2 pt-2 border-t mt-2">
                  <Label htmlFor="edit-tax_wrapper">{t("form.taxWrapper")}</Label>
                  <Select
                    value={editingAccount.tax_wrapper ?? "none"}
                    onValueChange={(v) => setEditingAccount({ ...editingAccount, tax_wrapper: v === "none" ? null : (v as TaxWrapper) })}
                  >
                    <SelectTrigger id="edit-tax_wrapper">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="none">{t("form.taxWrapperNone")}</SelectItem>
                      {TAX_WRAPPERS.map(w => (
                        <SelectItem key={w.value} value={w.value}>{t(`taxWrapper.${w.value}`)}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  {editingAccount.tax_wrapper && (
                    <>
                      <Label htmlFor="edit-opened_at">{t("form.openedAt")}</Label>
                      <Input
                        id="edit-opened_at"
                        type="date"
                        value={editingAccount.opened_at ?? ""}
                        onChange={(e) => setEditingAccount({ ...editingAccount, opened_at: e.target.value || null })}
                      />
                    </>
                  )}
                  <p className="text-xs text-slate-500">
                    {t("form.taxWrapperHint")}
                  </p>
                </div>
              )}

              {editingAccount.type === "investissement" && (
                <div className="grid gap-4 pt-2 border-t mt-2">
                  <h3 className="text-sm font-bold uppercase tracking-wider text-slate-500">{t("form.allocation")}</h3>
                  <div className="grid gap-2">
                    <Label htmlFor="edit-asset_class">{t("form.assetClass")}</Label>
                    <Input 
                      id="edit-asset_class" 
                      value={editingAccount.asset_class || ""} 
                      onChange={(e) => setEditingAccount({...editingAccount, asset_class: e.target.value})} 
                      list="edit-classes-list"
                    />
                    <datalist id="edit-classes-list">
                      {suggestions.asset_classes.map(c => <option key={c} value={c} />)}
                    </datalist>
                  </div>
                  <div className="grid gap-2">
                    <Label htmlFor="edit-sector">{t("form.sector")}</Label>
                    <Input 
                      id="edit-sector" 
                      value={editingAccount.sector || ""} 
                      onChange={(e) => setEditingAccount({...editingAccount, sector: e.target.value})} 
                      list="edit-sectors-list"
                    />
                    <datalist id="edit-sectors-list">
                      {suggestions.sectors.map(s => <option key={s} value={s} />)}
                    </datalist>
                  </div>
                  <div className="grid gap-2">
                    <Label htmlFor="edit-zone">{t("form.zone")}</Label>
                    <Input 
                      id="edit-zone" 
                      value={editingAccount.geographic_zone || ""} 
                      onChange={(e) => setEditingAccount({...editingAccount, geographic_zone: e.target.value})} 
                      list="edit-zones-list"
                    />
                    <datalist id="edit-zones-list">
                      {suggestions.geographic_zones.map(z => <option key={z} value={z} />)}
                    </datalist>
                  </div>
                </div>
              )}
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsEditDialogOpen(false)}>{tc("actions.cancel")}</Button>
            <Button onClick={() => handleUpdateAccount()} disabled={handleUpdateAccountBusy} className="bg-slate-900 text-white">{handleUpdateAccountBusy ? tc("actions.saving") : tc("actions.save")}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}
