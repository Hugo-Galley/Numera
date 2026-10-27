import { useCallback, useEffect, useState } from "react"
import { Copy, KeyRound, ShieldCheck } from "lucide-react"
import { api } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import { toast } from "sonner"

interface TotpStatus {
  enabled: boolean
  recovery_codes_left: number
}

interface TotpSetup {
  secret: string
  otpauth_uri: string
  qr_svg: string
}

type Step = "idle" | "password" | "scan" | "disable" | "regenerate"

const codeInputClass = "h-11 font-mono tracking-widest sm:h-10"

export function TotpCard() {
  const [status, setStatus] = useState<TotpStatus | null>(null)
  const [step, setStep] = useState<Step>("idle")
  const [password, setPassword] = useState("")
  const [code, setCode] = useState("")
  const [setup, setSetup] = useState<TotpSetup | null>(null)
  const [recoveryCodes, setRecoveryCodes] = useState<string[] | null>(null)
  const [busy, setBusy] = useState(false)

  const load = useCallback(async () => {
    try {
      setStatus(await api.get<TotpStatus>("/auth/totp/status"))
    } catch {
      /* carte non critique */
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const reset = () => {
    setStep("idle")
    setPassword("")
    setCode("")
    setSetup(null)
  }

  const run = async (action: () => Promise<void>) => {
    setBusy(true)
    try {
      await action()
    } catch (err: any) {
      toast.error(err?.message || "Opération impossible")
    } finally {
      setBusy(false)
    }
  }

  const startSetup = (e: React.FormEvent) => {
    e.preventDefault()
    run(async () => {
      setSetup(await api.post<TotpSetup>("/auth/totp/setup", { current_password: password }))
      setPassword("")
      setStep("scan")
    })
  }

  const confirmSetup = (e: React.FormEvent) => {
    e.preventDefault()
    run(async () => {
      const { recovery_codes } = await api.post<{ recovery_codes: string[] }>("/auth/totp/enable", { code })
      setRecoveryCodes(recovery_codes)
      reset()
      toast.success("Double authentification activée")
      load()
    })
  }

  const disable = (e: React.FormEvent) => {
    e.preventDefault()
    run(async () => {
      await api.post("/auth/totp/disable", { current_password: password, code })
      setRecoveryCodes(null)
      reset()
      toast.success("Double authentification désactivée")
      load()
    })
  }

  const regenerate = (e: React.FormEvent) => {
    e.preventDefault()
    run(async () => {
      const { recovery_codes } = await api.post<{ recovery_codes: string[] }>("/auth/totp/recovery-codes", { code })
      setRecoveryCodes(recovery_codes)
      reset()
      toast.success("Nouveaux codes de secours générés")
      load()
    })
  }

  const copyCodes = async () => {
    if (!recoveryCodes) return
    try {
      await navigator.clipboard.writeText(recoveryCodes.join("\n"))
      toast.success("Codes copiés")
    } catch {
      toast.error("Copie impossible")
    }
  }

  const codeField = (label: string) => (
    <div className="space-y-2">
      <Label htmlFor="totp-settings-code">{label}</Label>
      <Input
        id="totp-settings-code"
        autoComplete="one-time-code"
        autoCapitalize="none"
        autoCorrect="off"
        placeholder="123456"
        className={codeInputClass}
        value={code}
        onChange={(e) => setCode(e.target.value)}
        required
      />
    </div>
  )

  const passwordField = (
    <div className="space-y-2">
      <Label htmlFor="totp-settings-password">Mot de passe actuel</Label>
      <Input
        id="totp-settings-password"
        type="password"
        autoComplete="current-password"
        className="h-11 sm:h-10"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        required
      />
    </div>
  )

  const actions = (submitLabel: string) => (
    <div className="flex flex-col gap-2 sm:flex-row">
      <Button type="submit" disabled={busy} className="h-11 sm:h-10">
        {busy ? "En cours..." : submitLabel}
      </Button>
      <Button type="button" variant="ghost" onClick={reset} disabled={busy} className="h-11 sm:h-10">
        Annuler
      </Button>
    </div>
  )

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <ShieldCheck className="h-5 w-5" />
          Double authentification
          {status?.enabled && <Badge variant="secondary">Activée</Badge>}
        </CardTitle>
        <CardDescription>
          Un code de Google Authenticator (ou équivalent) est demandé après le mot de passe. La connexion par passkey
          n'est pas concernée : elle suffit à elle seule.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {recoveryCodes && (
          <div className="space-y-3 rounded-lg border border-amber-500/40 bg-amber-500/5 p-4" data-privacy-ignore>
            <p className="text-sm font-semibold">Codes de secours</p>
            <p className="text-sm text-muted-foreground">
              Garde-les en lieu sûr : chacun permet une connexion sans ton téléphone, une seule fois. Ils ne seront plus
              affichés.
            </p>
            <div className="grid grid-cols-2 gap-2 font-mono text-sm">
              {recoveryCodes.map((c) => (
                <span key={c} className="rounded bg-muted px-2 py-1 text-center">{c}</span>
              ))}
            </div>
            <div className="flex flex-col gap-2 sm:flex-row">
              <Button type="button" variant="outline" onClick={copyCodes} className="h-11 sm:h-10">
                <Copy className="mr-2 h-4 w-4" />
                Copier
              </Button>
              <Button type="button" variant="ghost" onClick={() => setRecoveryCodes(null)} className="h-11 sm:h-10">
                Je les ai notés
              </Button>
            </div>
          </div>
        )}

        {step === "idle" && status && !status.enabled && (
          <Button type="button" variant="outline" onClick={() => setStep("password")} className="h-11 w-full sm:w-auto">
            <ShieldCheck className="mr-2 h-4 w-4" />
            Activer
          </Button>
        )}

        {step === "idle" && status?.enabled && (
          <div className="space-y-3">
            <p className="text-sm text-muted-foreground">
              {status.recovery_codes_left} code{status.recovery_codes_left > 1 ? "s" : ""} de secours restant
              {status.recovery_codes_left > 1 ? "s" : ""}.
            </p>
            <div className="flex flex-col gap-2 sm:flex-row">
              <Button type="button" variant="outline" onClick={() => setStep("regenerate")} className="h-11 sm:h-10">
                <KeyRound className="mr-2 h-4 w-4" />
                Nouveaux codes de secours
              </Button>
              <Button type="button" variant="ghost" onClick={() => setStep("disable")} className="h-11 text-destructive sm:h-10">
                Désactiver
              </Button>
            </div>
          </div>
        )}

        {step === "password" && (
          <form onSubmit={startSetup} className="space-y-3">
            {passwordField}
            {actions("Continuer")}
          </form>
        )}

        {step === "scan" && setup && (
          <form onSubmit={confirmSetup} className="space-y-4">
            <p className="text-sm text-muted-foreground">
              Scanne ce QR code avec Google Authenticator, puis saisis le code affiché pour confirmer.
            </p>
            <img src={setup.qr_svg} alt="QR code de configuration" className="h-48 w-48 rounded-lg bg-white p-1" />
            <div className="space-y-1">
              <p className="text-xs text-muted-foreground">Ou saisis cette clé à la main :</p>
              <p className="break-all font-mono text-sm">{setup.secret.match(/.{1,4}/g)?.join(" ")}</p>
            </div>
            {codeField("Code à 6 chiffres")}
            {actions("Activer")}
          </form>
        )}

        {step === "disable" && (
          <form onSubmit={disable} className="space-y-3">
            {passwordField}
            {codeField("Code de l'application ou code de secours")}
            {actions("Désactiver")}
          </form>
        )}

        {step === "regenerate" && (
          <form onSubmit={regenerate} className="space-y-3">
            <p className="text-sm text-muted-foreground">Les anciens codes de secours ne fonctionneront plus.</p>
            {codeField("Code de l'application")}
            {actions("Générer")}
          </form>
        )}
      </CardContent>
    </Card>
  )
}
