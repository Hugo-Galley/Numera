import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { ICON_OPTIONS, IconComponent } from "@/components/dashboard/IconComponent"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { COLOR_OPTIONS } from "./types"
import type { CategoriesTabCtx } from "./useCategoriesTab"

/** Dialogue de modification d'une catégorie. */
export function EditCategoryDialog({ ctx }: { ctx: CategoriesTabCtx }) {
  const { editAnnualLimit, editCatColor, editCatGroup, editCatIcon, editCatName, editCatType, editMonthlyLimit, editOpen, handleUpdateCategory, handleUpdateCategoryBusy, setEditAnnualLimit, setEditCatColor, setEditCatGroup, setEditCatIcon, setEditCatName, setEditCatType, setEditMonthlyLimit, setEditOpen } = ctx
  return (
    <>
      <Dialog open={editOpen} onOpenChange={setEditOpen}>
        <DialogContent className="[&_input]:text-base md:[&_input]:text-sm sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle className="text-2xl font-bold">Modifier la catégorie</DialogTitle>
            <DialogDescription>Mettez à jour les informations de votre catégorie.</DialogDescription>
          </DialogHeader>
          <div className="grid gap-5 py-2 sm:gap-6 sm:py-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="grid gap-2">
                <Label htmlFor="edit-name" className="text-xs font-bold uppercase tracking-wider text-slate-500">Nom</Label>
                <Input 
                  id="edit-name" 
                  value={editCatName}
                  onChange={(e) => setEditCatName(e.target.value)}
                  className="bg-slate-50 border-slate-200"
                />
              </div>
              <div className="grid gap-2">
                <Label className="text-xs font-bold uppercase tracking-wider text-slate-500">Nature</Label>
                <Select value={editCatType} onValueChange={(v: any) => setEditCatType(v)}>
                  <SelectTrigger className="bg-slate-50 border-slate-200">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="depense">Dépense (-)</SelectItem>
                    <SelectItem value="revenu">Revenu (+)</SelectItem>
                    <SelectItem value="neutre">Neutre</SelectItem>
                  </SelectContent>
                  </Select>
                  </div>
                  </div>

                  <div className="grid gap-2">
                  <Label htmlFor="edit-group" className="text-xs font-bold uppercase tracking-wider text-slate-500">Groupe (pour Sankey)</Label>
                  <Input 
                  id="edit-group" 
                  placeholder="Ex: Vie courante, Loisirs..." 
                  value={editCatGroup}
                  onChange={(e) => setEditCatGroup(e.target.value)}
                  className="bg-slate-50 border-slate-200"
                  />
                  </div>

                  <div className="grid gap-2">
                  <Label className="text-xs font-bold uppercase tracking-wider text-slate-500">Icône</Label>

              <div className="p-3 bg-slate-50 rounded-xl border border-slate-200">
                <div className="grid grid-cols-6 sm:grid-cols-10 gap-1 sm:gap-2 max-h-[200px] overflow-y-auto pr-2 custom-scrollbar">
                  {ICON_OPTIONS.map((iconName) => (
                    <button
                      key={iconName}
                      type="button"
                      aria-label={`Icône ${iconName}`}
                      aria-pressed={editCatIcon === iconName}
                      onClick={() => setEditCatIcon(iconName)}
                      className={`p-3 sm:p-2 rounded-lg flex items-center justify-center transition-all ${editCatIcon === iconName ? 'bg-slate-900 text-white' : 'hover:bg-slate-200 text-slate-500'}`}
                    >
                      <IconComponent name={iconName} className="h-4 w-4" />
                    </button>
                  ))}
                </div>
              </div>
            </div>

            <div className="grid gap-2">
              <Label className="text-xs font-bold uppercase tracking-wider text-slate-500">Couleur</Label>
              <div className="flex flex-wrap gap-2 p-3 bg-slate-50 rounded-xl border border-slate-200">
                {COLOR_OPTIONS.map((opt) => (
                  <button
                    key={opt.name}
                    type="button"
                    onClick={() => setEditCatColor(opt.value)}
                    className={`h-10 w-10 sm:h-8 sm:w-8 rounded-full border-4 transition-all ${editCatColor === opt.value ? 'border-slate-300 scale-110' : 'border-transparent hover:scale-105'}`}
                    style={{ backgroundColor: opt.value }}
                    title={opt.name}
                  />
                ))}
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="grid gap-2">
                <Label htmlFor="edit-monthly-limit" className="text-xs font-bold uppercase tracking-wider text-slate-500">Limite mensuelle (€)</Label>
                <Input
                  id="edit-monthly-limit"
                  type="number" inputMode="decimal"
                  min="0"
                  placeholder="Ex: 200"
                  value={editMonthlyLimit}
                  onChange={(e) => setEditMonthlyLimit(e.target.value)}
                  className="bg-slate-50 border-slate-200"
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="edit-annual-limit" className="text-xs font-bold uppercase tracking-wider text-slate-500">Limite annuelle (€)</Label>
                <Input
                  id="edit-annual-limit"
                  type="number" inputMode="decimal"
                  min="0"
                  placeholder="Ex: 2400"
                  value={editAnnualLimit}
                  onChange={(e) => setEditAnnualLimit(e.target.value)}
                  className="bg-slate-50 border-slate-200"
                />
              </div>
            </div>

            <div className="theme-island flex items-center gap-4 p-4 bg-slate-900 rounded-2xl text-white">
              <div className="h-10 w-10 rounded-xl flex items-center justify-center" style={{ backgroundColor: editCatColor }}>
                <IconComponent name={editCatIcon} className="h-6 w-6 text-white" />
              </div>
              <div>
                <p className="text-sm font-bold">{editCatName || "Nom de la catégorie"}</p>
                <p className="text-[10px] uppercase font-black opacity-50 tracking-widest">{editCatType}</p>
              </div>
            </div>
          </div>
          <DialogFooter className="gap-2 sm:gap-0">
            <Button variant="ghost" className="h-11 sm:h-10" onClick={() => setEditOpen(false)}>Annuler</Button>
            <Button onClick={() => handleUpdateCategory()} disabled={handleUpdateCategoryBusy} className="h-11 bg-slate-900 text-white shadow-lg sm:h-10">Enregistrer les modifications</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}
