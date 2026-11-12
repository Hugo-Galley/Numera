import i18n from "i18next"
import { useTranslation } from "react-i18next"
import { appLocale } from "@/i18n/locale"
import { useEffect, useState } from "react"
import { AlertTriangle, CheckCircle2, DatabaseBackup, XCircle } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { getAdminBackupStatus, postAdminBackupRun } from "@/lib/api/settings"

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
  if (!value) return i18n.t("misc.never", { ns: "settings" })
  const date = new Date(value)
  const hours = Math.floor((Date.now() - date.getTime()) / 3_600_000)
  const label = date.toLocaleString(appLocale(), { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" })
  if (hours < 1) return i18n.t("misc.justNow", { ns: "settings", label })
  if (hours < 48) return i18n.t("misc.hoursAgo", { ns: "settings", hours, label })
  return i18n.t("misc.daysAgo", { ns: "settings", days: Math.floor(hours / 24), label })
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
  const { t } = useTranslation("settings")
  const [running, setRunning] = useState(false)
  const [outcome, setOutcome] = useState<Outcome | null>(null)
  const [status, setStatus] = useState<BackupStatus | null>(null)

  const loadStatus = () => {
    getAdminBackupStatus<BackupStatus>().then(setStatus).catch(() => setStatus(null))
  }
  useEffect(loadStatus, [])

  const run = async () => {
    setRunning(true)
    try {
      const res = await postAdminBackupRun<{ ok: boolean; github: boolean }>()
      setOutcome({ ok: true, github: res.github })
    } catch (err: any) {
      setOutcome({ ok: false, message: err?.message || t("backupCard.echecDeLaSauvegarde") })
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
          {t("backupCard.sauvegarde")}
        </CardTitle>
        <CardDescription>
          {t("backupCard.uneSauvegardeChiffreeEstFaite")}
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
                    {status.stale ? t("backupCard.aucuneSauvegardeDepuisPlusDe") : t("backupCard.laDerniereSauvegardeAEchoue")}
                    {status.last_error && ` Erreur : ${status.last_error}`}
                  </span>
                </div>
              )}
              <div className="divide-y divide-slate-100">
                <StatusRow
                  label={t("backupCard.derniereSauvegarde")}
                  value={formatAgo(status.last_backup_at)}
                  tone={status.stale ? "bad" : "ok"}
                />
                <StatusRow
                  label={t("backupCard.derniereSauvegardeAutomatique")}
                  value={formatAgo(status.last_auto_success_at)}
                  tone={status.last_auto_success_at ? "default" : "warn"}
                />
                <StatusRow
                  label={t("backupCard.chiffrement")}
                  value={status.encrypted ? t("backupCard.chiffreeBackupKey") : t("backupCard.nonChiffree")}
                  tone={status.encrypted ? "ok" : "warn"}
                />
                <StatusRow
                  label={t("backupCard.copieSurGithub")}
                  value={
                    !status.github_configured ? t("backupCard.nonConfiguree")
                    : status.github_error ? t("misc.githubFailed", { error: status.github_error })
                    : formatAgo(status.github_last_sync_at)
                  }
                  tone={!status.github_configured ? "warn" : status.github_error ? "bad" : "default"}
                />
                <StatusRow label={t("backupCard.sauvegardesConserveesSurLeServeur")} value={String(status.backup_count)} />
              </div>
            </div>
          ) : (
            <p className="rounded-lg bg-slate-50 p-3 text-sm text-slate-500">
              {t("backupCard.aucuneSauvegardeTrouveeSurCe")} <code>backup</code> {t("backupCard.docker")}
            </p>
          )
        )}
        <Button type="button" variant="outline" onClick={run} disabled={running} className="h-11 w-full sm:w-auto">
          <DatabaseBackup className="mr-2 h-4 w-4" />
          {running ? t("backupCard.sauvegardeEnCours") : t("backupCard.sauvegarderMaintenant")}
        </Button>
      </CardContent>

      <Dialog open={outcome !== null} onOpenChange={(open) => !open && setOutcome(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              {outcome?.ok ? <CheckCircle2 className="h-5 w-5 text-emerald-600" /> : <XCircle className="h-5 w-5 text-destructive" />}
              {outcome?.ok ? t("backupCard.sauvegardeTerminee") : t("backupCard.sauvegardeEchouee")}
            </DialogTitle>
            <DialogDescription>
              {outcome?.ok
                ? outcome.github
                  ? t("backupCard.laSauvegardeAEteCreee")
                  : t("misc.backupLocal")
                : outcome?.message}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button onClick={() => setOutcome(null)}>{t("backupCard.fermer")}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Card>
  )
}
