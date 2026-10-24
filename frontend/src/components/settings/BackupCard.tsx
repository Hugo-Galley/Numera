import { useState } from "react"
import { CheckCircle2, DatabaseBackup, XCircle } from "lucide-react"
import { api } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"

type Outcome = { ok: true; github: boolean } | { ok: false; message: string }

export function BackupCard() {
  const [running, setRunning] = useState(false)
  const [outcome, setOutcome] = useState<Outcome | null>(null)

  const run = async () => {
    setRunning(true)
    try {
      const res = await api.post<{ ok: boolean; github: boolean }>("/admin/backup/run")
      setOutcome({ ok: true, github: res.github })
    } catch (err: any) {
      setOutcome({ ok: false, message: err?.message || "Échec de la sauvegarde" })
    } finally {
      setRunning(false)
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <DatabaseBackup className="h-5 w-5" />
          Sauvegarde
        </CardTitle>
        <CardDescription>
          Crée une sauvegarde chiffrée de la base maintenant et l'envoie vers le dépôt GitHub privé si celui-ci est configuré.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Button type="button" variant="outline" onClick={run} disabled={running} className="h-11 w-full sm:w-auto">
          <DatabaseBackup className="mr-2 h-4 w-4" />
          {running ? "Sauvegarde en cours..." : "Sauvegarder maintenant"}
        </Button>
      </CardContent>

      <Dialog open={outcome !== null} onOpenChange={(open) => !open && setOutcome(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              {outcome?.ok ? <CheckCircle2 className="h-5 w-5 text-emerald-600" /> : <XCircle className="h-5 w-5 text-destructive" />}
              {outcome?.ok ? "Sauvegarde terminée" : "Sauvegarde échouée"}
            </DialogTitle>
            <DialogDescription>
              {outcome?.ok
                ? outcome.github
                  ? "La sauvegarde a été créée et envoyée sur GitHub."
                  : "La sauvegarde a été créée localement (envoi GitHub non configuré)."
                : outcome?.message}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button onClick={() => setOutcome(null)}>Fermer</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Card>
  )
}
