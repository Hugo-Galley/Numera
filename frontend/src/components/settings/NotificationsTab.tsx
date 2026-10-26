import { useEffect, useState } from "react"
import { Bell, Send } from "lucide-react"
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
import { api } from "@/lib/api"
import { errorMessage } from "@/lib/utils"

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
}

const SEVERITY_LABELS: Record<Severity, string> = {
  high: "Urgentes seulement",
  medium: "Importantes et urgentes",
  low: "Toutes",
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
  const [settings, setSettings] = useState<NotificationSettings | null>(null)
  const [draft, setDraft] = useState<NotificationSettings | null>(null)
  const [failed, setFailed] = useState(false)

  const load = async () => {
    setFailed(false)
    try {
      const data = await api.get<NotificationSettings>("/notifications/settings")
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

  const [handleSave, saving] = useSubmit(async () => {
    if (!draft) return
    try {
      const saved = await api.put<NotificationSettings>("/notifications/settings", draft)
      setSettings(saved)
      setDraft(saved)
      toast.success("Réglages des notifications enregistrés")
    } catch (error) {
      toast.error(errorMessage(error, "Enregistrement impossible"))
    }
  })

  const [handleTest, testing] = useSubmit(async (channel: "ntfy" | "telegram") => {
    try {
      await api.post("/notifications/test", { channel })
      toast.success(`Message de test envoyé sur ${channel === "ntfy" ? "ntfy" : "Telegram"}`)
    } catch (error) {
      toast.error(errorMessage(error, "Envoi impossible"))
    }
  })

  if (failed) return <ErrorState message="Impossible de charger les réglages des notifications." onRetry={load} />
  if (!draft || !settings) return <Skeleton className="h-96" />

  const dirty = JSON.stringify(draft) !== JSON.stringify(settings)

  return (
    <div className="space-y-6">
      <div>
        <h2 className="flex items-center gap-2 text-xl font-bold text-slate-900 md:text-2xl dark:text-slate-100">
          <Bell className="h-5 w-5" /> Notifications
        </h2>
        <p className="text-sm text-muted-foreground">
          Les nouvelles alertes du Centre d'Actions (budget, hausse d'abonnement, compte à vérifier…) arrivent sur votre téléphone, une seule fois chacune. Vérification toutes les heures.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">ntfy</CardTitle>
            <CardDescription>
              Installez l'app ntfy, abonnez-vous à un sujet difficile à deviner, puis renseignez-le ici. Vous pouvez aussi utiliser votre propre serveur ntfy.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <ToggleRow label="Activer ntfy" checked={draft.ntfy_enabled} onChange={(v) => set("ntfy_enabled", v)} />
            <div className="grid gap-2">
              <Label htmlFor="ntfy-server">Serveur</Label>
              <Input id="ntfy-server" value={draft.ntfy_server} onChange={(e) => set("ntfy_server", e.target.value)} placeholder="https://ntfy.sh" />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="ntfy-topic">Sujet</Label>
              <Input id="ntfy-topic" value={draft.ntfy_topic} onChange={(e) => set("ntfy_topic", e.target.value)} placeholder="numera-a8f3k2" autoComplete="off" />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="ntfy-token">Jeton d'accès (facultatif)</Label>
              <Input id="ntfy-token" type="password" value={draft.ntfy_token} onChange={(e) => set("ntfy_token", e.target.value)} autoComplete="off" />
            </div>
            <Button variant="outline" className="h-10" disabled={testing || dirty || !settings.ntfy_topic} onClick={() => handleTest("ntfy")}>
              <Send className="mr-2 h-4 w-4" /> Envoyer un test
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Telegram</CardTitle>
            <CardDescription>
              Créez un bot avec @BotFather, envoyez-lui un message, puis renseignez son jeton et votre identifiant de conversation (chat id).
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <ToggleRow label="Activer Telegram" checked={draft.telegram_enabled} onChange={(v) => set("telegram_enabled", v)} />
            <div className="grid gap-2">
              <Label htmlFor="tg-token">Jeton du bot</Label>
              <Input id="tg-token" type="password" value={draft.telegram_bot_token} onChange={(e) => set("telegram_bot_token", e.target.value)} autoComplete="off" />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="tg-chat">Chat id</Label>
              <Input id="tg-chat" inputMode="numeric" value={draft.telegram_chat_id} onChange={(e) => set("telegram_chat_id", e.target.value)} autoComplete="off" />
            </div>
            <Button
              variant="outline"
              className="h-10"
              disabled={testing || dirty || !settings.telegram_bot_token || !settings.telegram_chat_id}
              onClick={() => handleTest("telegram")}
            >
              <Send className="mr-2 h-4 w-4" /> Envoyer un test
            </Button>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Quoi envoyer</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-2 sm:max-w-sm">
            <Label>Alertes</Label>
            <Select value={draft.min_severity} onValueChange={(v) => set("min_severity", v as Severity)}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                {(["high", "medium", "low"] as Severity[]).map((s) => <SelectItem key={s} value={s}>{SEVERITY_LABELS[s]}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          <ToggleRow
            label="Résumé de la semaine"
            hint="Le dimanche soir : dépenses et revenus du mois, actions en cours, échéances des 7 jours à venir."
            checked={draft.weekly_digest}
            onChange={(v) => set("weekly_digest", v)}
          />
          <ToggleRow
            label="Masquer les montants"
            hint="Remplace les montants par ••• dans les messages (écran verrouillé, montre…)."
            checked={draft.hide_amounts}
            onChange={(v) => set("hide_amounts", v)}
          />
          <div className="grid gap-2">
            <Label htmlFor="notify-url">Adresse de votre instance Numera (facultatif)</Label>
            <Input id="notify-url" value={draft.public_url} onChange={(e) => set("public_url", e.target.value)} placeholder="https://numera.mondomaine.fr" />
            <p className="text-xs text-muted-foreground">Rend les notifications cliquables vers la bonne page.</p>
          </div>
        </CardContent>
      </Card>

      <div className="flex gap-2">
        <Button className="h-11 bg-slate-900 text-white hover:bg-slate-800 sm:h-10" disabled={!dirty || saving} onClick={() => handleSave()}>
          {saving ? "Enregistrement…" : "Enregistrer"}
        </Button>
        {dirty && <Button variant="ghost" className="h-11 sm:h-10" onClick={() => setDraft(settings)}>Annuler</Button>}
      </div>
    </div>
  )
}
