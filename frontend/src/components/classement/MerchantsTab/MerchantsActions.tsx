import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Plus, Wand2 } from "lucide-react"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { COLOR_OPTIONS } from "./types"
import type { MerchantsTabCtx } from "./useMerchantsTab"

/** Boutons d'en-tête : normalisation automatique et dialogue de création. */
export function MerchantsActions({ ctx }: { ctx: MerchantsTabCtx }) {
  const { categories, handleAddMerchant, handleAutoNormalize, newAliases, newCategoryId, newColor, newName, newOpen, setNewAliases, setNewCategoryId, setNewColor, setNewName, setNewOpen } = ctx
  return (
    <>
      <div className="grid grid-cols-1 gap-2 sm:flex">
        <Button variant="outline" onClick={handleAutoNormalize} className="h-11 border-slate-200 px-3 sm:h-10 sm:px-4">
          <Wand2 className="h-4 w-4 mr-2" /> Auto-normaliser
        </Button>
        <Dialog open={newOpen} onOpenChange={setNewOpen}>
          <DialogTrigger asChild>
            <Button className="h-11 w-full bg-slate-900 px-3 text-white hover:bg-slate-800 shadow-lg sm:h-10 sm:w-auto sm:px-4">
              <Plus className="h-4 w-4 mr-2" /> Nouveau marchand
            </Button>
          </DialogTrigger>
          <DialogContent className="[&_input]:text-base md:[&_input]:text-sm sm:max-w-[500px]">
            <DialogHeader>
              <DialogTitle className="text-2xl font-bold">Nouveau marchand canonique</DialogTitle>
              <DialogDescription>
                Définissez un nom propre et ses variantes de libellés.
              </DialogDescription>
            </DialogHeader>
            <div className="grid gap-5 py-2 sm:gap-6 sm:py-4">
              <div className="grid gap-2">
                <Label htmlFor="new-m-name" className="text-xs font-bold uppercase tracking-wider text-slate-500">Nom Canonique</Label>
                <Input 
                  id="new-m-name" 
                  placeholder="Ex: Amazon, Starbucks, Netflix..." 
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  className="bg-slate-50 border-slate-200"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="grid gap-2">
                  <Label className="text-xs font-bold uppercase tracking-wider text-slate-500">Catégorie par défaut</Label>
                  <Select value={newCategoryId} onValueChange={setNewCategoryId}>
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
                  <Select value={newColor} onValueChange={setNewColor}>
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

              <div className="grid gap-2">
                <Label htmlFor="new-aliases" className="text-xs font-bold uppercase tracking-wider text-slate-500">Variantes (séparées par des virgules)</Label>
                <Input 
                  id="new-aliases" 
                  placeholder="Ex: AMZN Digital, AMAZON.FR, AMZN FR..." 
                  value={newAliases}
                  onChange={(e) => setNewAliases(e.target.value)}
                  className="bg-slate-50 border-slate-200"
                />
              </div>
            </div>
            <DialogFooter className="gap-2 sm:gap-0">
              <Button variant="ghost" className="h-11 sm:h-10" onClick={() => setNewOpen(false)}>Annuler</Button>
              <Button onClick={handleAddMerchant} className="h-11 sm:h-10 bg-slate-900 text-white shadow-lg">Créer le marchand</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </>
  )
}
