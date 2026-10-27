import { useState } from "react"
import { AlertTriangle, Database } from "lucide-react"
import { toast } from "sonner"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { api } from "@/lib/api"

export function DangerZoneCard() {
  const [resetOpen, setResetOpen] = useState(false)
  const [resetConfirmText, setResetConfirmText] = useState("")
  const [resetPassword, setResetPassword] = useState("")

  return (
    <Card className="shadow-sm border-rose-100 overflow-hidden">
      <CardHeader className="bg-rose-50/50 border-b border-rose-100">
        <div className="flex items-center gap-2 text-rose-600">
          <AlertTriangle className="h-5 w-5" />
          <CardTitle className="text-lg">Zone de danger</CardTitle>
        </div>
        <CardDescription className="text-rose-600/70">Ces actions sont irréversibles.</CardDescription>
      </CardHeader>
      <CardContent className="p-4 sm:p-6">
        <div className="flex flex-col gap-4">
          <div className="p-4 sm:p-6 border border-rose-200 rounded-2xl bg-white space-y-4">
            <div>
              <p className="font-bold text-slate-900">Réinitialiser la base de données</p>
              <p className="text-sm text-slate-500">Supprime tous les comptes, transactions et catégories personnalisées.</p>
            </div>

            <Dialog open={resetOpen} onOpenChange={setResetOpen}>
              <DialogTrigger asChild>
                <Button
                  variant="destructive"
                  className="w-full bg-rose-600 hover:bg-rose-700 shadow-lg shadow-rose-200"
                >
                  <Database className="h-4 w-4 mr-2" /> Tout effacer définitivement
                </Button>
              </DialogTrigger>
              <DialogContent className="[&_input]:text-base md:[&_input]:text-sm sm:max-w-[425px]">
                <DialogHeader>
                  <DialogTitle className="text-2xl font-bold text-rose-600 flex items-center gap-2">
                    <AlertTriangle className="h-6 w-6" /> Attention
                  </DialogTitle>
                  <DialogDescription className="text-slate-900 font-medium pt-2">
                    Cette action est irréversible. Vous perdrez TOUTES vos données (comptes, transactions, catégories).
                  </DialogDescription>
                </DialogHeader>
                <div className="py-6 space-y-4">
                  <p className="text-sm text-slate-500">
                    Pour confirmer la suppression, veuillez taper <span className="font-black text-rose-600 select-all">EFFACER</span> ci-dessous :
                  </p>
                  <Input 
                    value={resetConfirmText}
                    onChange={(e) => setResetConfirmText(e.target.value)}
                    placeholder="Tapez EFFACER ici..."
                    className="bg-rose-50 border-rose-200 focus-visible:ring-rose-500 font-bold text-center"
                  />
                  <Input
                    type="password"
                    autoComplete="current-password"
                    value={resetPassword}
                    onChange={(e) => setResetPassword(e.target.value)}
                    placeholder="Mot de passe actuel"
                    aria-label="Mot de passe actuel"
                  />
                  <p className="text-xs text-slate-500">Un instantané de la base est enregistré avant l'effacement.</p>
                </div>
                <DialogFooter className="gap-2 sm:gap-0">
                  <Button variant="ghost" className="h-11 sm:h-10" onClick={() => { setResetOpen(false); setResetConfirmText(""); setResetPassword(""); }}>Annuler</Button>
                  <Button
                    variant="destructive"
                    className="h-11 sm:h-10"
                    disabled={resetConfirmText !== "EFFACER" || !resetPassword}
                    onClick={async () => {
                      try {
                        await api.post("/admin/reset-database", { 
                          confirm: true,
                          confirmation_code: resetConfirmText,
                          current_password: resetPassword
                        })
                        toast.success("Base réinitialisée avec succès")
                        window.location.reload()
                      } catch (error) {
                        toast.error(error instanceof Error ? error.message : "Erreur lors de la réinitialisation")
                      }
                    }}
                  >
                    Confirmer la suppression totale
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
