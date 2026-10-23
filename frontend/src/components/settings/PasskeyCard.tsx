import { useCallback, useEffect, useState } from "react"
import { Fingerprint, Trash2 } from "lucide-react"
import { api } from "@/lib/api"
import { createCredential, passkeySupported, serializeCredential } from "@/lib/passkey"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { useConfirm } from "@/providers/ConfirmProvider"
import { toast } from "sonner"

interface Passkey {
  id: string
  name: string
  created_at: string
  last_used_at: string | null
}

const formatDate = (iso: string) => new Date(iso).toLocaleDateString("fr-FR", { day: "numeric", month: "short", year: "numeric" })

export function PasskeyCard() {
  const [passkeys, setPasskeys] = useState<Passkey[]>([])
  const [busy, setBusy] = useState(false)
  const confirm = useConfirm()

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
    setBusy(true)
    try {
      const { options, state } = await api.post<{ options: any; state: string }>("/auth/passkey/register/options")
      const credential = await createCredential(options)
      if (!credential) return
      const name = /iPhone|iPad/.test(navigator.userAgent) ? "iPhone / iPad" : /Mac/.test(navigator.userAgent) ? "Mac" : "Appareil"
      await api.post("/auth/passkey/register/verify", { state, credential: serializeCredential(credential), name })
      toast.success("Passkey enregistrée")
      load()
    } catch (err: any) {
      if (err?.name !== "NotAllowedError") toast.error(err?.message || "Enregistrement impossible")
    } finally {
      setBusy(false)
    }
  }

  const remove = async (passkey: Passkey) => {
    if (!(await confirm(`Supprimer la passkey « ${passkey.name} » ? Elle ne pourra plus servir à se connecter.`, { destructive: true }))) return
    try {
      await api.delete(`/auth/passkey/${passkey.id}`)
      toast.success("Passkey supprimée")
      load()
    } catch (err: any) {
      toast.error(err?.message || "Suppression impossible")
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Fingerprint className="h-5 w-5" />
          Face ID / Touch ID
        </CardTitle>
        <CardDescription>
          Connectez-vous avec la biométrie de l'appareil. Le mot de passe reste utilisable. À enregistrer depuis l'adresse
          réellement utilisée (la passkey est liée au domaine).
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {passkeys.map((p) => (
          <div key={p.id} className="flex items-center justify-between rounded-lg border p-3">
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold">{p.name}</p>
              <p className="text-xs text-muted-foreground">
                Ajoutée le {formatDate(p.created_at)}
                {p.last_used_at ? ` · utilisée le ${formatDate(p.last_used_at)}` : ""}
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
            {busy ? "En cours..." : "Ajouter une passkey"}
          </Button>
        ) : (
          <p className="text-sm text-muted-foreground">Passkeys non prises en charge par ce navigateur.</p>
        )}
      </CardContent>
    </Card>
  )
}
