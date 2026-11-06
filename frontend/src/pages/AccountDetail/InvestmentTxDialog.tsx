import { useTranslation } from "react-i18next"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { COUNTRIES } from "@/lib/countries"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Plus } from "lucide-react"
import { SecuritySearchInput } from "@/components/investments/SecuritySearchInput"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import type { AccountDetailView } from "./useAccountDetail"

/** Dialogue des flux d'un compte d'investissement (versement, retrait, achat, vente, dividende, frais). */
export function InvestmentTxDialog({ ctx }: { ctx: AccountDetailView }) {
  const { t } = useTranslation("accountDetail")
  const { editInvTxId, handleCreateInvestmentTransaction, handleCreateInvestmentTransactionBusy, id, invTxAmount, invTxAssetClass, invTxCurrency, invTxDate, invTxFees, invTxIsin, invTxNote, invTxOpen, invTxQuantity, invTxReinvested, invTxSector, invTxTicker, invTxType, invTxUnitPrice, invTxWithholding, invTxZone, resetInvTxForm, setInvTxAmount, setInvTxAssetClass, setInvTxCurrency, setInvTxDate, setInvTxFees, setInvTxIsin, setInvTxNote, setInvTxOpen, setInvTxQuantity, setInvTxReinvested, setInvTxSector, setInvTxTicker, setInvTxType, setInvTxUnitPrice, setInvTxWithholding, setInvTxZone, suggestions } = ctx
  return (
    <>
      <Dialog open={invTxOpen} onOpenChange={(open) => { if (!open) { setInvTxOpen(false); resetInvTxForm(); } else { setInvTxOpen(true); } }}>
        <DialogTrigger asChild>
          <Button variant="outline" size="sm">
            <Plus className="h-4 w-4 mr-2" /> {t("investmentTxDialog.versementRetrait")}
          </Button>
        </DialogTrigger>
        <DialogContent className="max-sm:[&_input]:text-base sm:max-w-[425px] max-h-[calc(100dvh-2*max(1rem,env(safe-area-inset-top)))] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="text-2xl font-bold">{editInvTxId ? t("investmentTxDialog.modifierLeFlux") : t("investmentTxDialog.fluxDInvestissement")}</DialogTitle>
            <DialogDescription>{t("investmentTxDialog.enregistrezUnMouvementDeFonds")}</DialogDescription>
          </DialogHeader>
          <div className="grid gap-5 py-4 sm:gap-6 sm:py-6">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div className="grid gap-2">
                <Label className="text-xs uppercase tracking-wider font-bold text-slate-500">{t("investmentTxDialog.date")}</Label>
                <Input type="datetime-local" value={invTxDate} onChange={(e) => setInvTxDate(e.target.value)} className="bg-slate-50 border-slate-200" />
              </div>
              <div className="grid gap-2">
                <Label className="text-xs uppercase tracking-wider font-bold text-slate-500">{t("investmentTxDialog.type")}</Label>
                <Select value={invTxType} onValueChange={(v: any) => setInvTxType(v)}>
                  <SelectTrigger className="bg-slate-50 border-slate-200"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="versement">{t("investmentTxDialog.versement")}</SelectItem>
                    <SelectItem value="retrait">{t("investmentTxDialog.retrait")}</SelectItem>
                    <SelectItem value="dividende">{t("investmentTxDialog.dividendeGain")}</SelectItem>
                    <SelectItem value="achat">{t("investmentTxDialog.achatDeTitres")}</SelectItem>
                    <SelectItem value="vente">{t("investmentTxDialog.venteDeTitres")}</SelectItem>
                    <SelectItem value="frais">{t("investmentTxDialog.frais")}</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div className="grid gap-2">
                <Label htmlFor="ival" className="text-xs uppercase tracking-wider font-bold text-slate-500">{t("investmentTxDialog.montant")}</Label>
                <Input id="ival" type="number" inputMode="decimal" step="0.01" value={invTxAmount} onChange={(e) => setInvTxAmount(e.target.value)} placeholder="0.00" className="bg-slate-50 border-slate-200 font-bold text-lg" />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="icurrency" className="text-xs uppercase tracking-wider font-bold text-slate-500">{t("investmentTxDialog.devise")}</Label>
                <Select value={invTxCurrency} onValueChange={setInvTxCurrency}>
                  <SelectTrigger id="icurrency" className="bg-slate-50 border-slate-200"><SelectValue placeholder={t("investmentTxDialog.devise")} /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="EUR">{t("investmentTxDialog.eur")}</SelectItem>
                    <SelectItem value="USD">{t("investmentTxDialog.usd")}</SelectItem>
                    <SelectItem value="GBP">{t("investmentTxDialog.gbp")}</SelectItem>
                    <SelectItem value="CHF">{t("investmentTxDialog.chfChf")}</SelectItem>
                    <SelectItem value="JPY">{t("investmentTxDialog.jpy")}</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="grid gap-2">
              <Label htmlFor="inote" className="text-xs uppercase tracking-wider font-bold text-slate-500">{t("investmentTxDialog.note")}</Label>
              <Input id="inote" value={invTxNote} onChange={(e) => setInvTxNote(e.target.value)} placeholder={t("investmentTxDialog.optionnel")} className="bg-slate-50 border-slate-200" />
            </div>

            <div className="grid gap-3 pt-2 border-t">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-bold uppercase tracking-wider text-slate-500">{t("investmentTxDialog.actifBoursierTitreEtfAction")}</h3>
                <Badge variant="outline" className="text-[10px]">{invTxType === "dividende" || invTxType === "achat" || invTxType === "vente" ? t("investmentTxDialog.obligatoire") : t("investmentTxDialog.optionnel2")}</Badge>
              </div>

              <SecuritySearchInput
                ticker={invTxTicker}
                isin={invTxIsin}
                name={invTxNote}
                unitPrice={invTxUnitPrice}
                onSelectAsset={(asset) => {
                  setInvTxTicker(asset.symbol)
                  if (asset.isin) setInvTxIsin(asset.isin)
                  if (!invTxNote) setInvTxNote(asset.name)
                  if (asset.price_eur || asset.price) {
                    const p = (asset.price_eur || asset.price)!.toString()
                    setInvTxUnitPrice(p)
                    if (invTxType !== "dividende") {
                      if (invTxQuantity) {
                        setInvTxAmount((Number(invTxQuantity) * Number(p)).toFixed(2))
                      } else if (invTxAmount && Number(p) > 0) {
                        setInvTxQuantity((Number(invTxAmount) / Number(p)).toFixed(4))
                      }
                    }
                  }
                  if (asset.type === "ETF") setInvTxAssetClass("ETF")
                  else if (asset.type) setInvTxAssetClass("Actions")
                }}
                onChangeTicker={(t) => setInvTxTicker(t)}
                onChangeIsin={(isin) => setInvTxIsin(isin)}
                onChangeName={(name) => setInvTxNote(name)}
              />

              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 pt-1 border-t border-slate-100">
                <div className="grid gap-1">
                  <Label className="text-xs font-medium">{invTxType === "dividende" ? t("investmentTxDialog.partsRecuesSiReinvesti") : t("investmentTxDialog.nbDeParts")}</Label>
                  <Input
                    type="number" inputMode="decimal"
                    step="any"
                    min="0"
                    placeholder={t("investmentTxDialog.ex2")}
                    value={invTxQuantity}
                    onChange={(e) => {
                      const q = e.target.value
                      setInvTxQuantity(q)
                      if (q && invTxUnitPrice) {
                        setInvTxAmount((Number(q) * Number(invTxUnitPrice)).toFixed(2))
                      }
                    }}
                    className="bg-slate-50 border-slate-200 text-xs font-mono"
                  />
                </div>
                {invTxType !== "dividende" && (
                <div className="grid gap-1">
                  <Label className="text-xs font-medium">{t("investmentTxDialog.prixUnitaire")}</Label>
                  <Input
                    type="number" inputMode="decimal"
                    step="any"
                    min="0"
                    placeholder={t("investmentTxDialog.cours")}
                    value={invTxUnitPrice}
                    onChange={(e) => {
                      const p = e.target.value
                      setInvTxUnitPrice(p)
                      if (p && invTxQuantity) {
                        setInvTxAmount((Number(invTxQuantity) * Number(p)).toFixed(2))
                      }
                    }}
                    className="bg-slate-50 border-slate-200 text-xs font-mono"
                  />
                </div>
                )}
              </div>

              {invTxType === "dividende" && (
                <div className="grid gap-3 rounded-md border border-emerald-100 bg-emerald-50/50 p-3">
                  <div className="grid gap-1">
                    <Label className="text-xs font-medium">Retenue à la source ({invTxCurrency}, optionnel)</Label>
                    <Input
                      type="number" inputMode="decimal"
                      step="any"
                      min="0"
                      placeholder="0.00"
                      value={invTxWithholding}
                      onChange={(e) => setInvTxWithholding(e.target.value)}
                      className="bg-white border-slate-200 text-xs font-mono"
                    />
                    <p className="text-[11px] text-slate-500">{t("investmentTxDialog.leMontantSaisiPlusHaut")} <strong>{t("investmentTxDialog.netRecu")}</strong>{t("investmentTxDialog.commeDansLAppliDe")}</p>
                  </div>
                  <label className="flex items-center gap-2 text-xs font-medium text-slate-700">
                    <input
                      type="checkbox"
                      checked={invTxReinvested}
                      onChange={(e) => setInvTxReinvested(e.target.checked)}
                      className="h-4 w-4 rounded border-slate-300"
                    />
                    {t("investmentTxDialog.dividendeReinvestiAchatDeParts")}
                  </label>
                </div>
              )}

              {(invTxType === "achat" || invTxType === "vente") && (
                <div className="grid gap-1">
                  <Label className="text-xs font-medium">Frais de courtage ({invTxCurrency})</Label>
                  <Input
                    type="number" inputMode="decimal"
                    step="any"
                    min="0"
                    placeholder="0.00"
                    value={invTxFees}
                    onChange={(e) => setInvTxFees(e.target.value)}
                    className="bg-slate-50 border-slate-200 text-xs font-mono"
                  />
                  <p className="text-[11px] text-slate-500">{t("investmentTxDialog.inclusDansLePruLe")}</p>
                </div>
              )}

              {invTxTicker && invTxQuantity && invTxType !== "dividende" && invTxType !== "frais" && (
                <p className="text-[11px] text-emerald-600 font-medium">
                  ✓ Mettra à jour automatiquement votre position {invTxTicker.toUpperCase()} ({invTxType === "retrait" || invTxType === "vente" ? "-" : "+"}{invTxQuantity} parts).
                </p>
              )}
            </div>

            <div className="grid gap-4 pt-2 border-t">
              <h3 className="text-sm font-bold uppercase tracking-wider text-slate-500">{t("investmentTxDialog.assetAllocation")}</h3>
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div className="grid gap-2">
                  <Label htmlFor="aclass" className="text-xs uppercase tracking-wider font-bold text-slate-500">{t("investmentTxDialog.classeDActif")}</Label>
                  <Input 
                    id="aclass" 
                    value={invTxAssetClass} 
                    onChange={(e) => setInvTxAssetClass(e.target.value)} 
                    placeholder={t("investmentTxDialog.exActions")} 
                    className="bg-slate-50 border-slate-200" 
                    list="classes-list"
                  />
                  <datalist id="classes-list">
                    {suggestions.asset_classes.map(c => <option key={c} value={c} />)}
                  </datalist>
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="asector" className="text-xs uppercase tracking-wider font-bold text-slate-500">{t("investmentTxDialog.secteur")}</Label>
                  <Input 
                    id="asector" 
                    value={invTxSector} 
                    onChange={(e) => setInvTxSector(e.target.value)} 
                    placeholder={t("investmentTxDialog.exTech")} 
                    className="bg-slate-50 border-slate-200" 
                    list="sectors-list"
                  />
                  <datalist id="sectors-list">
                    {suggestions.sectors.map(s => <option key={s} value={s} />)}
                  </datalist>
                </div>
              </div>
              <div className="grid gap-2">
                <Label htmlFor="azone" className="text-xs uppercase tracking-wider font-bold text-slate-500">{t("investmentTxDialog.zoneGeoPays")}</Label>
                <Select value={invTxZone} onValueChange={setInvTxZone}>
                  <SelectTrigger className="bg-slate-50 border-slate-200">
                    <SelectValue placeholder={t("investmentTxDialog.selectionnerUnPays")} />
                  </SelectTrigger>
                  <SelectContent>
                    {COUNTRIES.map((c) => (
                      <SelectItem key={c.code} value={c.code}>{c.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => { setInvTxOpen(false); resetInvTxForm(); }}>{t("investmentTxDialog.annuler")}</Button>
            <Button onClick={() => handleCreateInvestmentTransaction()} disabled={handleCreateInvestmentTransactionBusy} className="bg-slate-900 text-white shadow-lg">{handleCreateInvestmentTransactionBusy ? t("investmentTxDialog.enregistrement") : t("investmentTxDialog.confirmer")}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}
