import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { LogoPicker } from "@/components/ui/LogoPicker"
import { Plus } from "lucide-react"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { TAX_WRAPPERS } from "./types"
import type { AccountsCtx } from "./useAccounts"

/** Dialogue de création d'un compte. */
export function CreateAccountDialog({ ctx }: { ctx: AccountsCtx }) {
  const { CURRENCIES, handleCreateAccount, handleCreateAccountBusy, isDialogOpen, newAssetClass, newCurrency, newEurosPct, newInstitution, newInvestisPct, newLogo, newName, newOpenedAt, newSector, newTaxWrapper, newType, newValuationMode, newZone, setIsDialogOpen, setNewAssetClass, setNewCurrency, setNewEurosPct, setNewInstitution, setNewInvestisPct, setNewLogo, setNewName, setNewOpenedAt, setNewSector, setNewTaxWrapper, setNewType, setNewValuationMode, setNewZone, suggestions } = ctx
  return (
    <>
      <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
        <DialogTrigger asChild>
          <Button className="bg-slate-900 text-white hover:bg-slate-800 w-full sm:w-auto">
            <Plus className="mr-2 h-4 w-4" /> Ajouter un compte
          </Button>
        </DialogTrigger>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Nouveau compte</DialogTitle>
            <DialogDescription>
              Ajoutez un nouveau compte pour suivre vos finances.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="name">Nom du compte</Label>
              <Input 
                id="name" 
                placeholder="Ex: Compte Courant Boursorama" 
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="institution">Établissement / Banque</Label>
              <Input 
                id="institution" 
                placeholder="Ex: BRED, SG, Boursorama, Fortuneo..." 
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
              <Label>Logo de la banque</Label>
              <LogoPicker value={newLogo} onChange={setNewLogo} suggestFor={newInstitution || newName} />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="type">Type de compte</Label>
              <Select value={newType} onValueChange={(v) => { setNewType(v); setNewValuationMode(v === "assurance_vie" ? "snapshot" : "positions") }}>
                <SelectTrigger>
                  <SelectValue placeholder="Sélectionnez un type" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="courant">Compte Courant</SelectItem>
                  <SelectItem value="epargne">Épargne</SelectItem>
                  <SelectItem value="investissement">Investissement</SelectItem>
                  <SelectItem value="assurance_vie">Assurance-Vie</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {newType === "assurance_vie" && (
              <div className="grid grid-cols-1 gap-4 pt-2 border-t mt-2 sm:grid-cols-2">
                <div className="grid gap-2">
                  <Label htmlFor="fonds_euros_pct">Fonds Euros (%)</Label>
                  <Input 
                    id="fonds_euros_pct" 
                    type="number" inputMode="decimal"
                    min="0"
                    max="100"
                    placeholder="Ex: 60" 
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
                  <Label htmlFor="fonds_investis_pct">Fonds Investis (%)</Label>
                  <Input 
                    id="fonds_investis_pct" 
                    type="number" inputMode="decimal"
                    min="0"
                    max="100"
                    placeholder="Ex: 40" 
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
              <Label htmlFor="currency">Devise</Label>
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
                <Label htmlFor="valuation_mode">Valorisation du compte</Label>
                <Select value={newValuationMode} onValueChange={(v) => setNewValuationMode(v as "positions" | "snapshot")}>
                  <SelectTrigger id="valuation_mode">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="positions">Calculée : positions × cours + espèces</SelectItem>
                    <SelectItem value="snapshot">Par relevés (snapshots) saisis</SelectItem>
                  </SelectContent>
                </Select>
                <p className="text-xs text-slate-500">
                  Choisis si la valeur du compte est calculée à partir des positions ou reprise du dernier relevé.
                </p>
              </div>
            )}

            {newType !== "courant" && (
              <div className="grid gap-2 pt-2 border-t mt-2">
                <Label htmlFor="tax_wrapper">Enveloppe fiscale</Label>
                <Select value={newTaxWrapper} onValueChange={setNewTaxWrapper}>
                  <SelectTrigger id="tax_wrapper">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">Aucune</SelectItem>
                    {TAX_WRAPPERS.map(w => (
                      <SelectItem key={w.value} value={w.value}>{w.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {newTaxWrapper !== "none" && (
                  <>
                    <Label htmlFor="opened_at">Date d'ouverture</Label>
                    <Input id="opened_at" type="date" value={newOpenedAt} onChange={(e) => setNewOpenedAt(e.target.value)} />
                  </>
                )}
                <p className="text-xs text-slate-500">
                  Active le suivi des plafonds et des dates clés dans la page Fiscalité.
                </p>
              </div>
            )}

            {newType === "investissement" && (
              <div className="grid gap-4 pt-2 border-t mt-2">
                <h3 className="text-sm font-bold uppercase tracking-wider text-slate-500">Asset Allocation</h3>
                <div className="grid gap-2">
                  <Label htmlFor="asset_class">Classe d'actif</Label>
                  <Input 
                    id="asset_class" 
                    placeholder="Ex: Actions, Crypto..." 
                    value={newAssetClass} 
                    onChange={(e) => setNewAssetClass(e.target.value)} 
                    list="classes-list"
                  />
                  <datalist id="classes-list">
                    {suggestions.asset_classes.map(c => <option key={c} value={c} />)}
                  </datalist>
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="sector">Secteur</Label>
                  <Input 
                    id="sector" 
                    placeholder="Ex: Tech, Santé..." 
                    value={newSector} 
                    onChange={(e) => setNewSector(e.target.value)} 
                    list="sectors-list"
                  />
                  <datalist id="sectors-list">
                    {suggestions.sectors.map(s => <option key={s} value={s} />)}
                  </datalist>
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="zone">Zone Géographique</Label>
                  <Input 
                    id="zone" 
                    placeholder="Ex: USA, Europe..." 
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
            <Button variant="outline" onClick={() => setIsDialogOpen(false)}>Annuler</Button>
            <Button onClick={() => handleCreateAccount()} disabled={handleCreateAccountBusy} className="bg-slate-900 text-white">{handleCreateAccountBusy ? "Création…" : "Créer"}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}
