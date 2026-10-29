import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { LogoPicker } from "@/components/ui/LogoPicker"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { TAX_WRAPPERS, TaxWrapper } from "./types"
import type { AccountsCtx } from "./useAccounts"

/** Dialogue de modification d'un compte. */
export function EditAccountDialog({ ctx }: { ctx: AccountsCtx }) {
  const { CURRENCIES, editingAccount, handleUpdateAccount, handleUpdateAccountBusy, isEditDialogOpen, setEditingAccount, setIsEditDialogOpen, suggestions } = ctx
  return (
    <>
      <Dialog open={isEditDialogOpen} onOpenChange={setIsEditDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Modifier le compte</DialogTitle>
            <DialogDescription>
              Mettez à jour les informations du compte.
            </DialogDescription>
          </DialogHeader>
          {editingAccount && (
            <div className="grid gap-4 py-4">
              <div className="grid gap-2">
                <Label htmlFor="edit-name">Nom du compte</Label>
                <Input 
                  id="edit-name" 
                  value={editingAccount.name}
                  onChange={(e) => setEditingAccount({...editingAccount, name: e.target.value})}
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="edit-institution">Établissement / Banque</Label>
                <Input 
                  id="edit-institution" 
                  placeholder="Ex: BRED, SG, Boursorama, Fortuneo..." 
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
                <Label>Logo de la banque</Label>
                <LogoPicker
                  value={editingAccount.logo || null}
                  onChange={(logo) => setEditingAccount({...editingAccount, logo})}
                  suggestFor={editingAccount.institution || editingAccount.name}
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="edit-type">Type de compte</Label>
                <Select 
                  value={editingAccount.type} 
                  onValueChange={(v) => setEditingAccount({...editingAccount, type: v as any})}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="courant">Compte Courant</SelectItem>
                    <SelectItem value="epargne">Épargne</SelectItem>
                    <SelectItem value="investissement">Investissement</SelectItem>
                    <SelectItem value="assurance_vie">Assurance-Vie</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {editingAccount.type === "assurance_vie" && (
                <div className="grid grid-cols-1 gap-4 pt-2 border-t mt-2 sm:grid-cols-2">
                  <div className="grid gap-2">
                    <Label htmlFor="edit-fonds_euros_pct">Fonds Euros (%)</Label>
                    <Input 
                      id="edit-fonds_euros_pct" 
                      type="number" inputMode="decimal"
                      min="0"
                      max="100"
                      placeholder="Ex: 60" 
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
                    <Label htmlFor="edit-fonds_investis_pct">Fonds Investis (%)</Label>
                    <Input 
                      id="edit-fonds_investis_pct" 
                      type="number" inputMode="decimal"
                      min="0"
                      max="100"
                      placeholder="Ex: 40" 
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
                <Label htmlFor="edit-currency">Devise</Label>
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
                  <Label htmlFor="edit-valuation_mode">Valorisation du compte</Label>
                  <Select value={editingAccount.valuation_mode ?? (editingAccount.type === "assurance_vie" ? "snapshot" : "positions")} onValueChange={(v) => setEditingAccount({...editingAccount, valuation_mode: v as "positions" | "snapshot"})}>
                    <SelectTrigger id="edit-valuation_mode">
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

              {editingAccount.type !== "courant" && (
                <div className="grid gap-2 pt-2 border-t mt-2">
                  <Label htmlFor="edit-tax_wrapper">Enveloppe fiscale</Label>
                  <Select
                    value={editingAccount.tax_wrapper ?? "none"}
                    onValueChange={(v) => setEditingAccount({ ...editingAccount, tax_wrapper: v === "none" ? null : (v as TaxWrapper) })}
                  >
                    <SelectTrigger id="edit-tax_wrapper">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="none">Aucune</SelectItem>
                      {TAX_WRAPPERS.map(w => (
                        <SelectItem key={w.value} value={w.value}>{w.label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  {editingAccount.tax_wrapper && (
                    <>
                      <Label htmlFor="edit-opened_at">Date d'ouverture</Label>
                      <Input
                        id="edit-opened_at"
                        type="date"
                        value={editingAccount.opened_at ?? ""}
                        onChange={(e) => setEditingAccount({ ...editingAccount, opened_at: e.target.value || null })}
                      />
                    </>
                  )}
                  <p className="text-xs text-slate-500">
                    Active le suivi des plafonds et des dates clés dans la page Fiscalité.
                  </p>
                </div>
              )}

              {editingAccount.type === "investissement" && (
                <div className="grid gap-4 pt-2 border-t mt-2">
                  <h3 className="text-sm font-bold uppercase tracking-wider text-slate-500">Asset Allocation</h3>
                  <div className="grid gap-2">
                    <Label htmlFor="edit-asset_class">Classe d'actif</Label>
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
                    <Label htmlFor="edit-sector">Secteur</Label>
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
                    <Label htmlFor="edit-zone">Zone Géographique</Label>
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
            <Button variant="outline" onClick={() => setIsEditDialogOpen(false)}>Annuler</Button>
            <Button onClick={() => handleUpdateAccount()} disabled={handleUpdateAccountBusy} className="bg-slate-900 text-white">{handleUpdateAccountBusy ? "Enregistrement…" : "Enregistrer"}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}
