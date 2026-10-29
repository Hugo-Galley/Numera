import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { TrendingUp } from "lucide-react"
import type { AccountDetailView } from "./useAccountDetail"

/** Dialogue de saisie d'un snapshot de valorisation. */
export function SnapshotDialog({ ctx }: { ctx: AccountDetailView }) {
  const { account, editSnapId, handleCreateSnapshot, handleCreateSnapshotBusy, id, resetSnapForm, setSnapDate, setSnapNote, setSnapOpen, setSnapValue, snapDate, snapNote, snapOpen, snapValue } = ctx
  return (
    <>
      <Dialog open={snapOpen} onOpenChange={(open) => { if (!open) { setSnapOpen(false); resetSnapForm(); } else { setSnapOpen(true); } }}>
        <DialogTrigger asChild>
          <Button size="sm" className="bg-slate-900 text-white hover:bg-slate-800">
            <TrendingUp className="h-4 w-4 mr-2" /> Nouveau Snapshot
          </Button>
        </DialogTrigger>
        <DialogContent className="max-sm:[&_input]:text-base sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle className="text-2xl font-bold">{editSnapId ? "Modifier le snapshot" : "Mettre à jour la valeur"}</DialogTitle>
            <DialogDescription>Définissez la valeur actuelle de votre support d'investissement.</DialogDescription>
          </DialogHeader>
          <div className="grid gap-5 py-4 sm:gap-6 sm:py-6">
            <div className="grid gap-2">
              <Label htmlFor="sdate" className="text-xs uppercase tracking-wider font-bold text-slate-500">Date</Label>
              <Input id="sdate" type="date" value={snapDate} onChange={(e) => setSnapDate(e.target.value)} className="bg-slate-50 border-slate-200" />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="sval" className="text-xs uppercase tracking-wider font-bold text-slate-500">Valeur Actuelle ({account?.currency || "EUR"})</Label>
              <Input id="sval" type="number" inputMode="decimal" step="0.01" value={snapValue} onChange={(e) => setSnapValue(e.target.value)} placeholder="0.00" className="bg-slate-50 border-slate-200 font-bold text-lg" />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="snote" className="text-xs uppercase tracking-wider font-bold text-slate-500">Note (Optionnel)</Label>
              <Input id="snote" value={snapNote} onChange={(e) => setSnapNote(e.target.value)} placeholder="Ex: Point mensuel..." className="bg-slate-50 border-slate-200" />
            </div>
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => { setSnapOpen(false); resetSnapForm(); }}>Annuler</Button>
            <Button onClick={() => handleCreateSnapshot()} disabled={handleCreateSnapshotBusy} className="bg-slate-900 text-white shadow-lg">{handleCreateSnapshotBusy ? "Enregistrement…" : "Mettre à jour"}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}
