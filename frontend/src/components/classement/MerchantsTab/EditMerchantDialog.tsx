import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Plus, X } from "lucide-react"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { COLOR_OPTIONS } from "./types"
import type { MerchantsTabCtx } from "./useMerchantsTab"

/** Dialogue de modification d'un marchand et de ses alias. */
export function EditMerchantDialog({ ctx }: { ctx: MerchantsTabCtx }) {
  const { categories, editCategoryId, editColor, editName, editOpen, editingMerchant, handleAddAlias, handleRemoveAlias, handleUpdateMerchant, newAliasLabel, setEditCategoryId, setEditColor, setEditName, setEditOpen, setNewAliasLabel } = ctx
  return (
    <>
      <Dialog open={editOpen} onOpenChange={setEditOpen}>
        <DialogContent className="[&_input]:text-base md:[&_input]:text-sm sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle className="text-2xl font-bold">Modifier le marchand</DialogTitle>
          </DialogHeader>
          <div className="grid gap-5 py-2 sm:gap-6 sm:py-4">
            <div className="grid gap-2">
              <Label htmlFor="edit-m-name" className="text-xs font-bold uppercase tracking-wider text-slate-500">Nom Canonique</Label>
              <Input 
                id="edit-m-name" 
                value={editName}
                onChange={(e) => setEditName(e.target.value)}
                className="bg-slate-50 border-slate-200"
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="grid gap-2">
                <Label className="text-xs font-bold uppercase tracking-wider text-slate-500">Catégorie par défaut</Label>
                <Select value={editCategoryId} onValueChange={setEditCategoryId}>
                  <SelectTrigger className="bg-slate-50 border-slate-200">
                    <SelectValue placeholder="Aucune" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">Aucune</SelectItem>
                    {categories.map(c => (
                      <SelectItem key={c.id} value={String(c.id)}>{c.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="grid gap-2">
                <Label className="text-xs font-bold uppercase tracking-wider text-slate-500">Couleur</Label>
                <Select value={editColor} onValueChange={setEditColor}>
                  <SelectTrigger className="bg-slate-50 border-slate-200">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {COLOR_OPTIONS.map(o => (
                      <SelectItem key={o.value} value={o.value}>
                        <div className="flex items-center gap-2">
                          <div className="h-3 w-3 rounded-full" style={{ backgroundColor: o.value }} />
                          {o.name}
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="space-y-3">
              <Label className="text-xs font-bold uppercase tracking-wider text-slate-500">Variantes de libellés</Label>
              <div className="flex flex-wrap gap-2 p-3 bg-slate-50 rounded-xl border border-slate-200 min-h-[60px]">
                {editingMerchant?.aliases.map(a => (
                  <Badge key={a.id} className="bg-white text-slate-700 border-slate-200 shadow-sm flex items-center gap-2 pr-1 h-9 sm:h-7">
                    {a.label}
                    <button aria-label="Fermer" 
                      onClick={() => handleRemoveAlias(a.id)}
                      className="h-7 w-7 sm:h-5 sm:w-5 rounded-md hover:bg-slate-100 flex items-center justify-center text-slate-400 hover:text-rose-500 transition-colors"
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </Badge>
                ))}
                {editingMerchant?.aliases.length === 0 && (
                  <p className="text-xs text-slate-400 italic">Aucune variante.</p>
                )}
              </div>

              <div className="flex gap-2">
                <Input 
                  placeholder="Nouvelle variante..." 
                  className="bg-white h-11 sm:h-9"
                  value={newAliasLabel}
                  onChange={(e) => setNewAliasLabel(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleAddAlias()}
                />
                <Button aria-label="Ajouter" size="sm" onClick={handleAddAlias} variant="secondary" className="h-11 w-11 px-3 sm:h-9 sm:w-auto">
                  <Plus className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </div>
          <DialogFooter className="gap-2 sm:gap-0">
            <Button variant="ghost" className="h-11 sm:h-10" onClick={() => setEditOpen(false)}>Annuler</Button>
            <Button onClick={handleUpdateMerchant} className="h-11 sm:h-10 bg-slate-900 text-white shadow-lg">Enregistrer</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}
