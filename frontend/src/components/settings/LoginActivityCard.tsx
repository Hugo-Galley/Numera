import i18n from "i18next"
import { useTranslation } from "react-i18next"
import { appLocale } from "@/i18n/locale"
import { useEffect, useState } from "react"
import { CheckCircle2, History, LogOut, XCircle } from "lucide-react"
import { toast } from "sonner"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { errorMessage } from "@/lib/utils"
import { useAuth } from "@/providers/AuthProvider"
import { useConfirm } from "@/providers/ConfirmProvider"
import { getAdminLoginEvents, postAdminLogoutAll } from "@/lib/api/settings"

interface LoginEvent {
  id: number
  created_at: string
  method: "password" | "password_totp" | "passkey" | string
  success: boolean
  reason: string | null
  ip: string | null
  user_agent: string | null
}

const METHOD_LABEL: Record<string, string> = {
  get password() { return i18n.t("misc.methodPassword", { ns: "settings" }) },
  get password_totp() { return i18n.t("misc.methodPasswordTotp", { ns: "settings" }) },
  passkey: "Face ID / Touch ID",
}

const REASON_LABEL: Record<string, string> = {
  get invalid_password() { return i18n.t("misc.reasonInvalidPassword", { ns: "settings" }) },
  get invalid_totp() { return i18n.t("misc.reasonInvalidTotp", { ns: "settings" }) },
  get invalid_passkey() { return i18n.t("misc.reasonInvalidPasskey", { ns: "settings" }) },
  get rate_limited() { return i18n.t("misc.reasonRateLimited", { ns: "settings" }) },
}

const VISIBLE = 8

// « Safari · iPhone » à partir du user-agent (approximatif, pour reconnaître ses appareils)
function deviceLabel(ua: string | null): string {
  if (!ua) return "Appareil inconnu"
  const device =
    /iPhone/.test(ua) ? "iPhone"
    : /iPad/.test(ua) ? "iPad"
    : /Android/.test(ua) ? "Android"
    : /Macintosh|Mac OS X/.test(ua) ? "Mac"
    : /Windows/.test(ua) ? "Windows"
    : /Linux/.test(ua) ? "Linux"
    : null
  const browser =
    /Edg\//.test(ua) ? "Edge"
    : /Firefox\//.test(ua) ? "Firefox"
    : /Chrome\//.test(ua) ? "Chrome"
    : /Safari\//.test(ua) ? "Safari"
    : /curl|python|httpx/i.test(ua) ? "Script"
    : null
  return [browser, device].filter(Boolean).join(" · ") || "Appareil inconnu"
}

// L'API renvoie des datetimes naïfs en UTC
function parseUtc(value: string): Date {
  return new Date(/[zZ]|[+-]\d\d:\d\d$/.test(value) ? value : `${value}Z`)
}

function formatWhen(value: string): string {
  return parseUtc(value).toLocaleString(appLocale(), { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" })
}

export function LoginActivityCard() {
  const { t } = useTranslation("settings")
  const confirm = useConfirm()
  const { logout } = useAuth()
  const [events, setEvents] = useState<LoginEvent[] | null>(null)
  const [failed, setFailed] = useState(false)
  const [showAll, setShowAll] = useState(false)

  useEffect(() => {
    getAdminLoginEvents<LoginEvent[]>("?limit=50")
      .then(setEvents)
      .catch(() => setFailed(true))
  }, [])

  const logoutEverywhere = async () => {
    const ok = await confirm(
      t("loginActivityCard.toutesLesSessionsOuvertesSeront"),
      { title: t("misc.signOutAllTitle"), confirmLabel: t("loginActivityCard.toutDeconnecter") },
    )
    if (!ok) return
    try {
      await postAdminLogoutAll()
      toast.success(t("loginActivityCard.tousLesAppareilsSontDeconnectes"))
      logout()
    } catch (error) {
      toast.error(errorMessage(error, t("loginActivityCard.impossibleDeDeconnecterLesAppareils")))
    }
  }

  const recentFailures = (events ?? []).filter(
    (e) => !e.success && Date.now() - parseUtc(e.created_at).getTime() < 7 * 24 * 3600 * 1000,
  ).length
  const visible = showAll ? events ?? [] : (events ?? []).slice(0, VISIBLE)

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <History className="h-5 w-5" />
          {t("loginActivityCard.connexions")}
        </CardTitle>
        <CardDescription>
          {t("loginActivityCard.lesDernieresTentativesDeConnexion")}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {recentFailures > 0 && (
          <p className="rounded-lg bg-amber-50 p-3 text-sm text-amber-800">
            {t("misc.failedAttempts", { count: recentFailures })}
          </p>
        )}

        {failed ? (
          <p className="text-sm text-rose-600">{t("loginActivityCard.impossibleDeChargerLHistorique")}</p>
        ) : events === null ? (
          <p className="text-sm text-slate-400">{t("loginActivityCard.chargement")}</p>
        ) : events.length === 0 ? (
          <p className="text-sm text-slate-500">{t("loginActivityCard.aucuneConnexionEnregistreePourL")}</p>
        ) : (
          <ul className="divide-y divide-slate-100 rounded-lg border border-slate-100">
            {visible.map((event) => (
              <li key={event.id} className="flex items-start justify-between gap-3 p-3">
                <div className="flex min-w-0 items-start gap-3">
                  {event.success ? (
                    <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-500" />
                  ) : (
                    <XCircle className="mt-0.5 h-4 w-4 shrink-0 text-rose-500" />
                  )}
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-slate-900">
                      {deviceLabel(event.user_agent)}
                      {event.ip && <span className="ml-2 text-xs font-normal text-slate-400">{event.ip}</span>}
                    </p>
                    <p className="text-xs text-slate-500">
                      {METHOD_LABEL[event.method] ?? event.method}
                      {!event.success && ` · ${REASON_LABEL[event.reason ?? ""] ?? t("misc.reasonFailed")}`}
                    </p>
                  </div>
                </div>
                <div className="flex shrink-0 flex-col items-end gap-1">
                  <span className="text-xs tabular-nums text-slate-500">{formatWhen(event.created_at)}</span>
                  {!event.success && (
                    <Badge variant="outline" className="border-rose-100 bg-rose-50 px-1.5 py-0 text-[10px] text-rose-700">{t("loginActivityCard.echec")}</Badge>
                  )}
                </div>
              </li>
            ))}
          </ul>
        )}

        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          {events && events.length > VISIBLE ? (
            <Button variant="ghost" size="sm" className="h-10 self-start text-slate-500" onClick={() => setShowAll(!showAll)}>
              {showAll ? t("loginActivityCard.afficherMoins") : t("misc.showAllN", { count: events.length })}
            </Button>
          ) : <span />}
          <Button variant="outline" className="h-11 gap-2 text-rose-600 hover:bg-rose-50 hover:text-rose-700 sm:h-10" onClick={logoutEverywhere}>
            <LogOut className="h-4 w-4" />
            {t("loginActivityCard.deconnecterTousLesAppareils")}
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
