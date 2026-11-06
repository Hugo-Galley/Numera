import { useTranslation } from "react-i18next"
import { appLocale } from "@/i18n/locale"
import { useCallback, useEffect, useState } from "react"
import { Fingerprint, Trash2 } from "lucide-react"
import { api } from "@/lib/api"
import { createCredential, passkeySupported, serializeCredential } from "@/lib/passkey"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { useConfirm } from "@/providers/ConfirmProvider"
import { toast } from "sonner"
import { useReauth } from "./ReauthDialog"

interface Passkey {
  id: string
  name: string
  created_at: string
  last_used_at: string | null
}

const formatDate = (iso: string) => new Date(iso).toLocaleDateString(appLocale(), { day: "numeric", month: "short", year: "numeric" })

export function PasskeyCard() {
  const { t } = useTranslation("settings")
  const [passkeys, setPasskeys] = useState<Passkey[]>([])
  const [busy, setBusy] = useState(false)
  const confirm = useConfirm()
  const { ask, dialog } = useReauth()

  const load = useCallback(async () => {
    try {
      setPasskeys(await api.get<Passkey[]>("/auth/passkey"))
    } catch {
      /* liste non critique */
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const register = async () => {
    const auth = await ask(t("misc.addPasskeyTitle"), t("misc.addPasskeyHint"))
    if (!auth) return
    setBusy(true)
    try {
      const { options, state } = await api.post<{ options: any; state: string }>("/auth/passkey/register/options", { current_password: auth.current_password })
      const credential = await createCredential(options)
      if (!credential) return
      const name = /iPhone|iPad/.test(navigator.userAgent) ? "iPhone / iPad" : /Mac/.test(navigator.userAgent) ? "Mac" : "Appareil"
      await api.post("/auth/passkey/register/verify", { state, credential: serializeCredential(credential), name, ...auth })
      toast.success(t("passkeyCard.passkeyEnregistree"))
      load()
    } catch (err: any) {
      if (err?.name !== "NotAllowedError") toast.error(err?.message || t("passkeyCard.enregistrementImpossible"))
    } finally {
      setBusy(false)
    }
  }

  const remove = async (passkey: Passkey) => {
    if (!(await confirm(t("misc.removePasskeyConfirm", { name: passkey.name }), { destructive: true }))) return
    const auth = await ask(t("misc.removePasskeyTitle"), t("misc.removePasskeyHint"))
    if (!auth) return
    try {
      await api.delete(`/auth/passkey/${passkey.id}`, auth)
      toast.success(t("passkeyCard.passkeySupprimee"))
      load()
    } catch (err: any) {
      toast.error(err?.message || t("passkeyCard.suppressionImpossible"))
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Fingerprint className="h-5 w-5" />
          {t("passkeyCard.faceIdTouchId")}
        </CardTitle>
        <CardDescription>
          {t("passkeyCard.connectezVousAvecLaBiometrie")}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {passkeys.map((p) => (
          <div key={p.id} className="flex items-center justify-between rounded-lg border p-3">
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold">{p.name}</p>
              <p className="text-xs text-muted-foreground">
                {t("misc.addedOn", { date: formatDate(p.created_at) })}
                {p.last_used_at ? t("misc.usedOn", { date: formatDate(p.last_used_at) }) : ""}
              </p>
            </div>
            <Button variant="ghost" size="icon" className="h-11 w-11 shrink-0" onClick={() => remove(p)} aria-label={`Supprimer ${p.name}`}>
              <Trash2 className="h-4 w-4 text-destructive" />
            </Button>
          </div>
        ))}
        {passkeySupported() ? (
          <Button type="button" variant="outline" onClick={register} disabled={busy} className="h-11 w-full sm:w-auto">
            <Fingerprint className="mr-2 h-4 w-4" />
            {busy ? t("passkeyCard.enCours") : t("passkeyCard.ajouterUnePasskey")}
          </Button>
        ) : (
          <p className="text-sm text-muted-foreground">{t("passkeyCard.passkeysNonPrisesEnCharge")}</p>
        )}
      </CardContent>
      {dialog}
    </Card>
  )
}
