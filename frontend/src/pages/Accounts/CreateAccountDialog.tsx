import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { LogoPicker } from "@/components/ui/LogoPicker"
import { Plus } from "lucide-react"
import { useTranslation } from "react-i18next"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { TAX_WRAPPERS } from "./types"
import type { AccountsCtx } from "./useAccounts"

/** Dialogue de création d'un compte. */
export function CreateAccountDialog({ ctx }: { ctx: AccountsCtx }) {
  const { t } = useTranslation("accounts")
  const { t: tc } = useTranslation("common")
  const { CURRENCIES, handleCreateAccount, handleCreateAccountBusy, isDialogOpen, newAssetClass, newCurrency, newEurosPct, newInstitution, newInvestisPct, newLogo, newName, newOpenedAt, newSector, newTaxWrapper, newType, newValuationMode, newZone, setIsDialogOpen, setNewAssetClass, setNewCurrency, setNewEurosPct, setNewInstitution, setNewInvestisPct, setNewLogo, setNewName, setNewOpenedAt, setNewSector, setNewTaxWrapper, setNewType, setNewValuationMode, setNewZone, suggestions } = ctx
  return (
    <>
      <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
        <DialogTrigger asChild>
          <Button className="bg-slate-900 text-white hover:bg-slate-800 w-full sm:w-auto">
            <Plus className="mr-2 h-4 w-4" /> {t("form.addAccount")}
          </Button>
        </DialogTrigger>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t("form.newTitle")}</DialogTitle>
            <DialogDescription>
              {t("form.newSubtitle")}
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="name">{t("form.name")}</Label>
              <Input 
                id="name" 
                placeholder={t("form.namePlaceholder")} 
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="institution">{t("form.institution")}</Label>
              <Input 
                id="institution" 
                placeholder={t("form.institutionPlaceholder")} 
                value={newInstitution}
                onChange={(e) => setNewInstitution(e.target.value)}
                list="institutions-list"
              />
              <datalist id="institutions-list">
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
              <LogoPicker value={newLogo} onChange={setNewLogo} suggestFor={newInstitution || newName} />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="type">{t("form.type")}</Label>
              <Select value={newType} onValueChange={(v) => { setNewType(v); setNewValuationMode(v === "assurance_vie" ? "snapshot" : "positions") }}>
                <SelectTrigger>
                  <SelectValue placeholder={t("form.typePlaceholder")} />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="courant">{tc("accountTypes.courant")}</SelectItem>
                  <SelectItem value="epargne">{tc("accountTypes.epargne")}</SelectItem>
                  <SelectItem value="investissement">{tc("accountTypes.investissement")}</SelectItem>
                  <SelectItem value="assurance_vie">{tc("accountTypes.assurance_vie")}</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {newType === "assurance_vie" && (
              <div className="grid grid-cols-1 gap-4 pt-2 border-t mt-2 sm:grid-cols-2">
                <div className="grid gap-2">
                  <Label htmlFor="fonds_euros_pct">{t("form.euroFunds")}</Label>
                  <Input 
                    id="fonds_euros_pct" 
                    type="number" inputMode="decimal"
                    min="0"
                    max="100"
                    placeholder={t("form.example", { value: 60 })} 
                    value={newEurosPct} 
                    onChange={(e) => {
                      const val = e.target.value;
                      setNewEurosPct(val);
                      const num = parseFloat(val);
                      if (!isNaN(num) && num >= 0 && num <= 100) {
                        setNewInvestisPct(String(100 - num));
                      }
                    }} 
                  />
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="fonds_investis_pct">{t("form.investedFunds")}</Label>
                  <Input 
                    id="fonds_investis_pct" 
                    type="number" inputMode="decimal"
                    min="0"
                    max="100"
                    placeholder={t("form.example", { value: 40 })} 
                    value={newInvestisPct} 
                    onChange={(e) => {
                      const val = e.target.value;
                      setNewInvestisPct(val);
                      const num = parseFloat(val);
                      if (!isNaN(num) && num >= 0 && num <= 100) {
                        setNewEurosPct(String(100 - num));
                      }
                    }} 
                  />
                </div>
              </div>
            )}
            <div className="grid gap-2">
              <Label htmlFor="currency">{t("form.currency")}</Label>
              <Select value={newCurrency} onValueChange={setNewCurrency}>
                <SelectTrigger>
                  <SelectValue placeholder="EUR" />
                </SelectTrigger>
                <SelectContent>
                  {CURRENCIES.map(c => (
                    <SelectItem key={c} value={c}>{c}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {(newType === "investissement" || newType === "assurance_vie") && (
              <div className="grid gap-2 pt-2 border-t mt-2">
                <Label htmlFor="valuation_mode">{t("form.valuation")}</Label>
                <Select value={newValuationMode} onValueChange={(v) => setNewValuationMode(v as "positions" | "snapshot")}>
                  <SelectTrigger id="valuation_mode">
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

            {newType !== "courant" && (
              <div className="grid gap-2 pt-2 border-t mt-2">
                <Label htmlFor="tax_wrapper">{t("form.taxWrapper")}</Label>
                <Select value={newTaxWrapper} onValueChange={setNewTaxWrapper}>
                  <SelectTrigger id="tax_wrapper">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">{t("form.taxWrapperNone")}</SelectItem>
                    {TAX_WRAPPERS.map(w => (
                      <SelectItem key={w.value} value={w.value}>{t(`taxWrapper.${w.value}`)}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {newTaxWrapper !== "none" && (
                  <>
                    <Label htmlFor="opened_at">{t("form.openedAt")}</Label>
                    <Input id="opened_at" type="date" value={newOpenedAt} onChange={(e) => setNewOpenedAt(e.target.value)} />
                  </>
                )}
                <p className="text-xs text-slate-500">
                  {t("form.taxWrapperHint")}
                </p>
              </div>
            )}

            {newType === "investissement" && (
              <div className="grid gap-4 pt-2 border-t mt-2">
                <h3 className="text-sm font-bold uppercase tracking-wider text-slate-500">{t("form.allocation")}</h3>
                <div className="grid gap-2">
                  <Label htmlFor="asset_class">{t("form.assetClass")}</Label>
                  <Input 
                    id="asset_class" 
                    placeholder={t("form.assetClassPlaceholder")} 
                    value={newAssetClass} 
                    onChange={(e) => setNewAssetClass(e.target.value)} 
                    list="classes-list"
                  />
                  <datalist id="classes-list">
                    {suggestions.asset_classes.map(c => <option key={c} value={c} />)}
                  </datalist>
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="sector">{t("form.sector")}</Label>
                  <Input 
                    id="sector" 
                    placeholder={t("form.sectorPlaceholder")} 
                    value={newSector} 
                    onChange={(e) => setNewSector(e.target.value)} 
                    list="sectors-list"
                  />
                  <datalist id="sectors-list">
                    {suggestions.sectors.map(s => <option key={s} value={s} />)}
                  </datalist>
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="zone">{t("form.zone")}</Label>
                  <Input 
                    id="zone" 
                    placeholder={t("form.zonePlaceholder")} 
                    value={newZone} 
                    onChange={(e) => setNewZone(e.target.value)} 
                    list="zones-list"
                  />
                  <datalist id="zones-list">
                    {suggestions.geographic_zones.map(z => <option key={z} value={z} />)}
                  </datalist>
                </div>
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsDialogOpen(false)}>{tc("actions.cancel")}</Button>
            <Button onClick={() => handleCreateAccount()} disabled={handleCreateAccountBusy} className="bg-slate-900 text-white">{handleCreateAccountBusy ? t("form.creating") : t("form.create")}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}
