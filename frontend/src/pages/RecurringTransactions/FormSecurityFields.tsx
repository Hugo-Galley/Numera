import { Badge } from "@/components/ui/badge"
import { COUNTRIES } from "@/lib/countries"
import { Checkbox } from "@/components/ui/checkbox"
import { CompanyLogo } from "@/components/ui/CompanyLogo"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { SecuritySearchInput } from "@/components/investments/SecuritySearchInput"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Sparkles } from "lucide-react"
import type { RecurringTransactionsCtx } from "./useRecurringTransactions"

/** Formulaire : titre investi (DCA) et classification de l'actif. */
export function FormSecurityFields({ ctx }: { ctx: RecurringTransactionsCtx }) {
  const { formData, isManualQuantityOpen, setFormData, setIsManualQuantityOpen, showSecurities, suggestions } = ctx
  return (
    <>
      {/* Investment Asset DCA block */}
      <div className="grid gap-3 p-3.5 border rounded-lg bg-slate-50/70">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CompanyLogo
              ticker={formData.ticker}
              name={formData.name}
              isin={formData.isin}
              className="h-5 w-5 rounded-xs shrink-0"
            />
            <span className="text-xs font-bold uppercase tracking-wider text-slate-700">
              Actif Boursier / Titre (ETF, Action)
            </span>
          </div>
          <Badge variant="outline" className="text-[10px] font-normal">
            Optionnel
          </Badge>
        </div>

        <SecuritySearchInput
          ticker={formData.ticker}
          isin={formData.isin}
          name={formData.name}
          unitPrice={formData.unit_price}
          onSelectAsset={(asset) => {
            setFormData((prev) => {
              const p = asset.price_eur || asset.price || prev.unit_price
              return {
                ...prev,
                name: prev.name.trim() ? prev.name : asset.name,
                ticker: asset.symbol,
                isin: asset.isin || prev.isin,
                unit_price: p ? p.toString() : prev.unit_price,
                asset_class: asset.type === "ETF" ? "ETF" : "Actions",
                etf_profile_id: asset.etf_profile_id || null,
              }
            })
          }}
          onChangeTicker={(t) => setFormData((prev) => ({ ...prev, ticker: t }))}
          onChangeIsin={(isin) => setFormData((prev) => ({ ...prev, isin }))}
          onChangeName={(name) => setFormData((prev) => ({ ...prev, name }))}
        />

        {/* Automatic Shares Calculation (DCA) or Manual Override */}
        {formData.ticker && (
          <div className="space-y-2 pt-1 border-t border-slate-200/60">
            <div className="p-3 bg-blue-50/70 border border-blue-200/60 rounded-xl space-y-1.5">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5 text-xs font-bold text-blue-900">
                  <Sparkles className="h-3.5 w-3.5 text-blue-600" />
                  <span>Calcul automatique des parts (DCA)</span>
                </div>
                <Badge variant="outline" className="text-[10px] bg-white text-blue-700 border-blue-200 font-semibold">
                  Auto
                </Badge>
              </div>
              <p className="text-[11px] text-blue-800/80 leading-relaxed">
                Le nombre de parts sera calculé automatiquement le jour de chaque transaction au cours réel du marché (<code className="font-mono text-[10px] bg-blue-100/60 px-1 py-0.5 rounded">Parts = Montant / Cours</code>).
              </p>
              {formData.amount && formData.unit_price && Number(formData.unit_price) > 0 && (
                <div className="pt-1.5 text-[11px] font-semibold text-blue-900 flex items-center justify-between border-t border-blue-200/40">
                  <span className="text-blue-700/80">Estimation au cours actuel ({Number(formData.unit_price).toLocaleString("fr-FR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} €) :</span>
                  <span className="font-mono font-bold text-blue-950 bg-white px-2 py-0.5 rounded shadow-xs">
                    ~ {(Number(formData.amount) / Number(formData.unit_price)).toFixed(4)} parts
                  </span>
                </div>
              )}
            </div>

            {!formData.quantity && (
              <label className="flex items-start gap-2 p-2.5 rounded-xl border border-slate-200/80 bg-white cursor-pointer">
                <Checkbox
                  checked={formData.whole_shares}
                  onCheckedChange={(v) => setFormData(prev => ({ ...prev, whole_shares: v === true }))}
                  className="mt-0.5 rounded-md h-4 w-4"
                />
                <span className="text-[11px] leading-relaxed text-slate-700">
                  <span className="font-semibold text-slate-900">Parts entières (PEA)</span>
                  {" "}: arrondit à l'entier inférieur et n'investit que le coût des parts. Le reliquat reste en espèces chez le courtier.
                </span>
              </label>
            )}

            <div className="flex items-center justify-between pt-0.5">
              <button
                type="button"
                onClick={() => setIsManualQuantityOpen(!isManualQuantityOpen)}
                className="text-[11px] text-slate-500 hover:text-slate-800 font-medium underline underline-offset-2"
              >
                {isManualQuantityOpen ? "Masquer la saisie manuelle de parts" : "Fixer un nombre de parts précis (Optionnel)"}
              </button>
              {isManualQuantityOpen && formData.quantity && (
                <button
                  type="button"
                  onClick={() => {
                    setFormData(prev => ({ ...prev, quantity: "" }))
                    setIsManualQuantityOpen(false)
                  }}
                  className="text-[10px] text-red-500 hover:underline"
                >
                  Revenir au calcul auto
                </button>
              )}
            </div>

            {isManualQuantityOpen && (
              <div className="grid grid-cols-2 gap-3 p-3 bg-slate-50 rounded-xl border border-slate-200/80">
                <div className="grid gap-1">
                  <Label htmlFor="quantity" className="text-xs text-slate-600 font-medium">Nb de parts fixe</Label>
                  <Input
                    id="quantity"
                    type="number" inputMode="decimal"
                    step="any"
                    min="0"
                    placeholder="Ex: 1.5 (Laisser vide pour auto)"
                    value={formData.quantity}
                    onChange={(e) => {
                      const q = e.target.value
                      setFormData(prev => ({ ...prev, quantity: q }))
                    }}
                    className="bg-white text-xs font-mono"
                  />
                </div>
                <div className="grid gap-1">
                  <Label htmlFor="unit_price" className="text-xs text-slate-600 font-medium">Cours indicatif (€)</Label>
                  <Input
                    id="unit_price"
                    type="number" inputMode="decimal"
                    step="any"
                    min="0"
                    placeholder="Cours indicatif..."
                    value={formData.unit_price}
                    onChange={(e) => {
                      const p = e.target.value
                      setFormData(prev => ({ ...prev, unit_price: p }))
                    }}
                    className="bg-white text-xs font-mono"
                  />
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {showSecurities && (
        <div className="grid grid-cols-1 gap-4 p-3 border rounded-md bg-slate-50/50">
          <h3 className="text-sm font-bold uppercase tracking-wider text-slate-500">Asset Allocation</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="grid gap-2">
              <Label htmlFor="aclass" className="text-xs uppercase tracking-wider font-bold text-slate-500">Classe d'actif</Label>
              <Input 
                id="aclass" 
                value={formData.asset_class} 
                onChange={(e) => setFormData({ ...formData, asset_class: e.target.value })} 
                placeholder="Ex: Actions..." 
                className="bg-white border-slate-200" 
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
                value={formData.sector} 
                onChange={(e) => setFormData({ ...formData, sector: e.target.value })} 
                placeholder="Ex: Tech..." 
                className="bg-white border-slate-200" 
                list="sectors-list"
              />
              <datalist id="sectors-list">
                {suggestions.sectors.map(s => <option key={s} value={s} />)}
              </datalist>
            </div>
          </div>
          <div className="grid gap-2">
            <Label htmlFor="azone" className="text-xs uppercase tracking-wider font-bold text-slate-500">Zone Géo / Pays</Label>
            <Select value={formData.geographic_zone} onValueChange={(v) => setFormData({ ...formData, geographic_zone: v })}>
              <SelectTrigger className="bg-white border-slate-200">
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
      )}
    </>
  )
}
