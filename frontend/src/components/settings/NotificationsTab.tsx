import i18n from "i18next"
import { useTranslation } from "react-i18next"
import { useEffect, useState } from "react"
import { Send } from "lucide-react"
import { toast } from "sonner"

import { ErrorState } from "@/components/layout/ErrorState"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Skeleton } from "@/components/ui/skeleton"
import { Switch } from "@/components/ui/switch"
import { useSubmit } from "@/hooks/useSubmit"
import { type Language } from "@/i18n"
import { api } from "@/lib/api"
import { syncServerLanguage } from "@/lib/serverLanguage"
import { errorMessage } from "@/lib/utils"
import { useReauth } from "./ReauthDialog"

// Destinations d'envoi et masquage des montants : changer l'un d'eux exige le mot de passe actuel
const SENSITIVE_FIELDS = [
  "ntfy_server", "ntfy_topic", "ntfy_token", "telegram_bot_token", "telegram_chat_id", "hide_amounts", "public_url",
] as const

type Severity = "low" | "medium" | "high"

interface NotificationSettings {
  ntfy_enabled: boolean
  ntfy_server: string
  ntfy_topic: string
  ntfy_token: string
  telegram_enabled: boolean
  telegram_bot_token: string
  telegram_chat_id: string
  min_severity: Severity
  weekly_digest: boolean
  hide_amounts: boolean
  public_url: string
  language?: Language
}

const SEVERITY_LABELS: Record<Severity, string> = {
  get high() { return i18n.t("misc.sevHigh", { ns: "settings" }) },
  get medium() { return i18n.t("misc.sevMedium", { ns: "settings" }) },
  get low() { return i18n.t("misc.sevLow", { ns: "settings" }) },
}

function ToggleRow({ label, hint, checked, onChange }: { label: string; hint?: string; checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <label className="flex min-h-11 items-center justify-between gap-4">
      <span>
        <span className="block text-sm font-medium">{label}</span>
        {hint && <span className="block text-xs text-muted-foreground">{hint}</span>}
      </span>
      <Switch checked={checked} onCheckedChange={onChange} />
    </label>
  )
}

export function NotificationsTab() {
  const { t } = useTranslation("settings")
  const [settings, setSettings] = useState<NotificationSettings | null>(null)
  const [draft, setDraft] = useState<NotificationSettings | null>(null)
  const [failed, setFailed] = useState(false)
  const { ask, dialog } = useReauth()

  const load = async () => {
    setFailed(false)
    try {
      let data = await api.get<NotificationSettings>("/notifications/settings")
      if (data.language && data.language !== i18n.language) {
        // Les notifications partent du serveur : elles suivent la langue choisie dans l'interface
        const language = i18n.language as Language
        await syncServerLanguage(language)
        data = { ...data, language }
      }
      setSettings(data)
      setDraft(data)
    } catch (error) {
      console.error("Failed to load notification settings", error)
      setFailed(true)
    }
  }

  useEffect(() => { load() }, [])

  const set = <K extends keyof NotificationSettings>(key: K, value: NotificationSettings[K]) =>
    setDraft((d) => (d ? { ...d, [key]: value } : d))

  const persist = async (): Promise<boolean> => {
    if (!draft || !settings) return false
    const sensitiveChanged = SENSITIVE_FIELDS.some((field) => draft[field] !== settings[field])
    let auth: { current_password: string } | null = null
    if (sensitiveChanged) {
      auth = await ask(t("misc.confirmChange"), t("misc.confirmChangeHint"))
      if (!auth) return false
    }
    try {
      const saved = await api.put<NotificationSettings>("/notifications/settings", { ...draft, ...(auth ? { current_password: auth.current_password } : {}) })
      setSettings(saved)
      setDraft(saved)
      toast.success(t("notificationsTab.reglagesDesNotificationsEnregistres"))
      return true
    } catch (error) {
      toast.error(errorMessage(error, t("notificationsTab.enregistrementImpossible")))
      return false
    }
  }

  const [handleSave, saving] = useSubmit(persist)

  // Le test lit les réglages en base : on enregistre d'abord les modifications en cours
  const [handleTest, testing] = useSubmit(async (channel: "ntfy" | "telegram") => {
    if (dirty && !(await persist())) return
    try {
      await api.post("/notifications/test", { channel })
      toast.success(t("misc.testSent", { channel: channel === "ntfy" ? "ntfy" : "Telegram" }))
    } catch (error) {
      toast.error(errorMessage(error, t("notificationsTab.envoiImpossible")))
    }
  })

  const dirty = JSON.stringify(draft) !== JSON.stringify(settings)

  if (failed) return <ErrorState message={t("notificationsTab.impossibleDeChargerLesReglages")} onRetry={load} />
  if (!draft || !settings) return <Skeleton className="h-96" />

  const busy = testing || saving
  const ntfyReady = !!draft.ntfy_topic.trim()
  const telegramReady = !!draft.telegram_bot_token.trim() && !!draft.telegram_chat_id.trim()

  return (
    <div className="space-y-6">
      <div>
        <p className="text-sm text-muted-foreground">
          {t("notificationsTab.lesNouvellesAlertesDuCentre")}
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">ntfy</CardTitle>
            <CardDescription>
              {t("notificationsTab.installezLAppNtfyAbonnez")}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <ToggleRow label={t("notificationsTab.activerNtfy")} checked={draft.ntfy_enabled} onChange={(v) => set("ntfy_enabled", v)} />
            <div className="grid gap-2">
              <Label htmlFor="ntfy-server">{t("notificationsTab.serveur")}</Label>
              <Input id="ntfy-server" value={draft.ntfy_server} onChange={(e) => set("ntfy_server", e.target.value)} placeholder="https://ntfy.sh" />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="ntfy-topic">{t("notificationsTab.sujet")}</Label>
              <Input id="ntfy-topic" value={draft.ntfy_topic} onChange={(e) => set("ntfy_topic", e.target.value)} placeholder="numera-a8f3k2" autoComplete="off" />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="ntfy-token">{t("notificationsTab.jetonDAccesFacultatif")}</Label>
              <Input id="ntfy-token" type="password" value={draft.ntfy_token} onChange={(e) => set("ntfy_token", e.target.value)} autoComplete="off" />
            </div>
            <Button variant="outline" className="h-10" disabled={busy || !ntfyReady} onClick={() => handleTest("ntfy")}>
              <Send className="mr-2 h-4 w-4" /> {dirty ? t("notificationsTab.enregistrerEtTester") : t("notificationsTab.envoyerUnTest")}
            </Button>
            {!ntfyReady && <p className="text-xs text-muted-foreground">{t("notificationsTab.renseignezUnSujetPourEnvoyer")}</p>}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Telegram</CardTitle>
            <CardDescription>
              {t("notificationsTab.creezUnBotAvecBotfather")}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <ToggleRow label={t("notificationsTab.activerTelegram")} checked={draft.telegram_enabled} onChange={(v) => set("telegram_enabled", v)} />
            <div className="grid gap-2">
              <Label htmlFor="tg-token">{t("notificationsTab.jetonDuBot")}</Label>
              <Input id="tg-token" type="password" value={draft.telegram_bot_token} onChange={(e) => set("telegram_bot_token", e.target.value)} autoComplete="off" />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="tg-chat">{t("notificationsTab.chatId")}</Label>
              <Input id="tg-chat" inputMode="numeric" value={draft.telegram_chat_id} onChange={(e) => set("telegram_chat_id", e.target.value)} autoComplete="off" />
            </div>
            <Button
              variant="outline"
              className="h-10"
              disabled={busy || !telegramReady}
              onClick={() => handleTest("telegram")}
            >
              <Send className="mr-2 h-4 w-4" /> {dirty ? t("notificationsTab.enregistrerEtTester") : t("notificationsTab.envoyerUnTest")}
            </Button>
            {!telegramReady && <p className="text-xs text-muted-foreground">{t("notificationsTab.renseignezLeJetonDuBot")}</p>}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">{t("notificationsTab.quoiEnvoyer")}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-2 sm:max-w-sm">
            <Label>{t("notificationsTab.alertes")}</Label>
            <Select value={draft.min_severity} onValueChange={(v) => set("min_severity", v as Severity)}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                {(["high", "medium", "low"] as Severity[]).map((s) => <SelectItem key={s} value={s}>{SEVERITY_LABELS[s]}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          <ToggleRow
            label={t("notificationsTab.resumeDeLaSemaine")}
            hint={t("notificationsTab.leDimancheSoirDepensesEt")}
            checked={draft.weekly_digest}
            onChange={(v) => set("weekly_digest", v)}
          />
          <ToggleRow
            label={t("notificationsTab.masquerLesMontants")}
            hint={t("notificationsTab.remplaceLesMontantsParDans")}
            checked={draft.hide_amounts}
            onChange={(v) => set("hide_amounts", v)}
          />
          <div className="grid gap-2">
            <Label htmlFor="notify-url">{t("notificationsTab.adresseDeVotreInstanceNumera")}</Label>
            <Input id="notify-url" value={draft.public_url} onChange={(e) => set("public_url", e.target.value)} placeholder={t("notificationsTab.httpsNumeraMondomaineFr")} />
            <p className="text-xs text-muted-foreground">{t("notificationsTab.rendLesNotificationsCliquablesVers")}</p>
          </div>
        </CardContent>
      </Card>

      <div className="flex gap-2">
        <Button className="h-11 bg-slate-900 text-white hover:bg-slate-800 sm:h-10" disabled={!dirty || saving} onClick={() => handleSave()}>
          {saving ? t("notificationsTab.enregistrement") : t("notificationsTab.enregistrer")}
        </Button>
        {dirty && <Button variant="ghost" className="h-11 sm:h-10" onClick={() => setDraft(settings)}>{t("notificationsTab.annuler")}</Button>}
      </div>
      {dialog}
    </div>
  )
}
