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
  const { editInvTxId, handleCreateInvestmentTransaction, handleCreateInvestmentTransactionBusy, id, invTxAmount, invTxAssetClass, invTxCurrency, invTxDate, invTxFees, invTxIsin, invTxNote, invTxOpen, invTxQuantity, invTxReinvested, invTxSector, invTxTicker, invTxType, invTxUnitPrice, invTxWithholding, invTxZone, resetInvTxForm, setInvTxAmount, setInvTxAssetClass, setInvTxCurrency, setInvTxDate, setInvTxFees, setInvTxIsin, setInvTxNote, setInvTxOpen, setInvTxQuantity, setInvTxReinvested, setInvTxSector, setInvTxTicker, setInvTxType, setInvTxUnitPrice, setInvTxWithholding, setInvTxZone, suggestions } = ctx
  return (
    <>
      <Dialog open={invTxOpen} onOpenChange={(open) => { if (!open) { setInvTxOpen(false); resetInvTxForm(); } else { setInvTxOpen(true); } }}>
        <DialogTrigger asChild>
          <Button variant="outline" size="sm">
            <Plus className="h-4 w-4 mr-2" /> Versement / Retrait
          </Button>
        </DialogTrigger>
        <DialogContent className="max-sm:[&_input]:text-base sm:max-w-[425px] max-h-[calc(100dvh-2*max(1rem,env(safe-area-inset-top)))] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="text-2xl font-bold">{editInvTxId ? "Modifier le flux" : "Flux d'investissement"}</DialogTitle>
            <DialogDescription>Enregistrez un mouvement de fonds sur ce compte.</DialogDescription>
          </DialogHeader>
          <div className="grid gap-5 py-4 sm:gap-6 sm:py-6">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div className="grid gap-2">
                <Label className="text-xs uppercase tracking-wider font-bold text-slate-500">Date</Label>
                <Input type="datetime-local" value={invTxDate} onChange={(e) => setInvTxDate(e.target.value)} className="bg-slate-50 border-slate-200" />
              </div>
              <div className="grid gap-2">
                <Label className="text-xs uppercase tracking-wider font-bold text-slate-500">Type</Label>
                <Select value={invTxType} onValueChange={(v: any) => setInvTxType(v)}>
                  <SelectTrigger className="bg-slate-50 border-slate-200"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="versement">Versement (+)</SelectItem>
                    <SelectItem value="retrait">Retrait (-)</SelectItem>
                    <SelectItem value="dividende">Dividende (Gain)</SelectItem>
                    <SelectItem value="achat">Achat de titres</SelectItem>
                    <SelectItem value="vente">Vente de titres</SelectItem>
                    <SelectItem value="frais">Frais</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div className="grid gap-2">
                <Label htmlFor="ival" className="text-xs uppercase tracking-wider font-bold text-slate-500">Montant</Label>
                <Input id="ival" type="number" inputMode="decimal" step="0.01" value={invTxAmount} onChange={(e) => setInvTxAmount(e.target.value)} placeholder="0.00" className="bg-slate-50 border-slate-200 font-bold text-lg" />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="icurrency" className="text-xs uppercase tracking-wider font-bold text-slate-500">Devise</Label>
                <Select value={invTxCurrency} onValueChange={setInvTxCurrency}>
                  <SelectTrigger id="icurrency" className="bg-slate-50 border-slate-200"><SelectValue placeholder="Devise" /></SelectTrigger>
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
              <Label htmlFor="inote" className="text-xs uppercase tracking-wider font-bold text-slate-500">Note</Label>
              <Input id="inote" value={invTxNote} onChange={(e) => setInvTxNote(e.target.value)} placeholder="Optionnel..." className="bg-slate-50 border-slate-200" />
            </div>

            <div className="grid gap-3 pt-2 border-t">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-bold uppercase tracking-wider text-slate-500">Actif Boursier / Titre (ETF, Action)</h3>
                <Badge variant="outline" className="text-[10px]">{invTxType === "dividende" || invTxType === "achat" || invTxType === "vente" ? "Obligatoire" : "Optionnel"}</Badge>
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
                  <Label className="text-xs font-medium">{invTxType === "dividende" ? "Parts reçues (si réinvesti)" : "Nb de parts"}</Label>
                  <Input
                    type="number" inputMode="decimal"
                    step="any"
                    min="0"
                    placeholder="Ex: 2"
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
                  <Label className="text-xs font-medium">Prix unitaire</Label>
                  <Input
                    type="number" inputMode="decimal"
                    step="any"
                    min="0"
                    placeholder="Cours..."
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
                    <p className="text-[11px] text-slate-500">Le montant saisi plus haut est le <strong>net reçu</strong>, comme dans l'appli de ton courtier.</p>
                  </div>
                  <label className="flex items-center gap-2 text-xs font-medium text-slate-700">
                    <input
                      type="checkbox"
                      checked={invTxReinvested}
                      onChange={(e) => setInvTxReinvested(e.target.checked)}
                      className="h-4 w-4 rounded border-slate-300"
                    />
                    Dividende réinvesti (achat de parts avec ce montant)
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
                  <p className="text-[11px] text-slate-500">Inclus dans le PRU. Le montant correspond au total débité (achat) ou crédité (vente).</p>
                </div>
              )}

              {invTxTicker && invTxQuantity && invTxType !== "dividende" && invTxType !== "frais" && (
                <p className="text-[11px] text-emerald-600 font-medium">
                  ✓ Mettra à jour automatiquement votre position {invTxTicker.toUpperCase()} ({invTxType === "retrait" || invTxType === "vente" ? "-" : "+"}{invTxQuantity} parts).
                </p>
              )}
            </div>

            <div className="grid gap-4 pt-2 border-t">
              <h3 className="text-sm font-bold uppercase tracking-wider text-slate-500">Asset Allocation</h3>
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div className="grid gap-2">
                  <Label htmlFor="aclass" className="text-xs uppercase tracking-wider font-bold text-slate-500">Classe d'actif</Label>
                  <Input 
                    id="aclass" 
                    value={invTxAssetClass} 
                    onChange={(e) => setInvTxAssetClass(e.target.value)} 
                    placeholder="Ex: Actions..." 
                    className="bg-slate-50 border-slate-200" 
                    list="classes-list"
                  />
                  <datalist id="classes-list">
                    {suggestions.asset_classes.map(c => <option key={c} value={c} />)}
                  </datalist>
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="asector" className="text-xs uppercase tracking-wider font-bold text-slate-500">Secteur</Label>
                  <Input 
                    id="asector" 
                    value={invTxSector} 
                    onChange={(e) => setInvTxSector(e.target.value)} 
                    placeholder="Ex: Tech..." 
                    className="bg-slate-50 border-slate-200" 
                    list="sectors-list"
                  />
                  <datalist id="sectors-list">
                    {suggestions.sectors.map(s => <option key={s} value={s} />)}
                  </datalist>
                </div>
              </div>
              <div className="grid gap-2">
                <Label htmlFor="azone" className="text-xs uppercase tracking-wider font-bold text-slate-500">Zone Géo / Pays</Label>
                <Select value={invTxZone} onValueChange={setInvTxZone}>
                  <SelectTrigger className="bg-slate-50 border-slate-200">
                    <SelectValue placeholder="Sélectionner un pays..." />
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
            <Button variant="ghost" onClick={() => { setInvTxOpen(false); resetInvTxForm(); }}>Annuler</Button>
            <Button onClick={() => handleCreateInvestmentTransaction()} disabled={handleCreateInvestmentTransactionBusy} className="bg-slate-900 text-white shadow-lg">{handleCreateInvestmentTransactionBusy ? "Enregistrement…" : "Confirmer"}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}
