import { useEffect, useState } from "react"
import { AlertTriangle, CheckCircle2, DatabaseBackup, XCircle } from "lucide-react"
import { api } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"

type Outcome = { ok: true; github: boolean } | { ok: false; message: string }

interface BackupStatus {
  configured: boolean
  last_backup_at: string | null
  last_backup_file: string | null
  encrypted: boolean | null
  backup_count: number
  last_auto_success_at: string | null
  last_error: string | null
  last_error_at: string | null
  github_configured: boolean
  github_last_sync_at: string | null
  github_error: string | null
  stale: boolean
}

function formatAgo(value: string | null): string {
  if (!value) return "jamais"
  const date = new Date(value)
  const hours = Math.floor((Date.now() - date.getTime()) / 3_600_000)
  const label = date.toLocaleString("fr-FR", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" })
  if (hours < 1) return `à l'instant (${label})`
  if (hours < 48) return `il y a ${hours} h (${label})`
  return `il y a ${Math.floor(hours / 24)} jours (${label})`
}

function StatusRow({ label, value, tone = "default" }: { label: string; value: string; tone?: "default" | "ok" | "warn" | "bad" }) {
  const color = { default: "text-slate-900", ok: "text-emerald-600", warn: "text-amber-600", bad: "text-rose-600" }[tone]
  return (
    <div className="flex flex-col gap-0.5 py-2 sm:flex-row sm:items-baseline sm:justify-between sm:gap-4">
      <span className="text-sm text-slate-500">{label}</span>
      <span className={`text-sm font-medium sm:text-right ${color}`}>{value}</span>
    </div>
  )
}

export function BackupCard() {
  const [running, setRunning] = useState(false)
  const [outcome, setOutcome] = useState<Outcome | null>(null)
  const [status, setStatus] = useState<BackupStatus | null>(null)

  const loadStatus = () => {
    api.get<BackupStatus>("/admin/backup/status").then(setStatus).catch(() => setStatus(null))
  }
  useEffect(loadStatus, [])

  const run = async () => {
    setRunning(true)
    try {
      const res = await api.post<{ ok: boolean; github: boolean }>("/admin/backup/run")
      setOutcome({ ok: true, github: res.github })
    } catch (err: any) {
      setOutcome({ ok: false, message: err?.message || "Échec de la sauvegarde" })
    } finally {
      setRunning(false)
      loadStatus()
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
          Une sauvegarde chiffrée est faite toutes les 24 h, puis envoyée vers le dépôt GitHub privé s'il est configuré. Le Centre d'actions te prévient si elle n'a pas tourné depuis 2 jours.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {status && (
          status.configured ? (
            <div className="space-y-3">
              {(status.stale || status.last_error) && (
                <div className="flex gap-2 rounded-lg bg-rose-50 p-3 text-sm text-rose-700">
                  <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                  <span>
                    {status.stale ? "Aucune sauvegarde depuis plus de 2 jours." : "La dernière sauvegarde a échoué."}
                    {status.last_error && ` Erreur : ${status.last_error}`}
                  </span>
                </div>
              )}
              <div className="divide-y divide-slate-100">
                <StatusRow
                  label="Dernière sauvegarde"
                  value={formatAgo(status.last_backup_at)}
                  tone={status.stale ? "bad" : "ok"}
                />
                <StatusRow
                  label="Dernière sauvegarde automatique"
                  value={formatAgo(status.last_auto_success_at)}
                  tone={status.last_auto_success_at ? "default" : "warn"}
                />
                <StatusRow
                  label="Chiffrement"
                  value={status.encrypted ? "Chiffrée (BACKUP_KEY)" : "Non chiffrée"}
                  tone={status.encrypted ? "ok" : "warn"}
                />
                <StatusRow
                  label="Copie sur GitHub"
                  value={
                    !status.github_configured ? "Non configurée"
                    : status.github_error ? `En échec : ${status.github_error}`
                    : formatAgo(status.github_last_sync_at)
                  }
                  tone={!status.github_configured ? "warn" : status.github_error ? "bad" : "default"}
                />
                <StatusRow label="Sauvegardes conservées sur le serveur" value={String(status.backup_count)} />
              </div>
            </div>
          ) : (
            <p className="rounded-lg bg-slate-50 p-3 text-sm text-slate-500">
              Aucune sauvegarde trouvée sur ce serveur : les sauvegardes automatiques tournent avec le conteneur <code>backup</code> (Docker).
            </p>
          )
        )}
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
