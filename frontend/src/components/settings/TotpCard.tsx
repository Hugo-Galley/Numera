import { useTranslation } from "react-i18next"
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
  const { t } = useTranslation("settings")
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
      toast.error(err?.message || t("totpCard.operationImpossible"))
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
      toast.success(t("totpCard.doubleAuthentificationActivee"))
      load()
    })
  }

  const disable = (e: React.FormEvent) => {
    e.preventDefault()
    run(async () => {
      await api.post("/auth/totp/disable", { current_password: password, code })
      setRecoveryCodes(null)
      reset()
      toast.success(t("totpCard.doubleAuthentificationDesactivee"))
      load()
    })
  }

  const regenerate = (e: React.FormEvent) => {
    e.preventDefault()
    run(async () => {
      const { recovery_codes } = await api.post<{ recovery_codes: string[] }>("/auth/totp/recovery-codes", { code })
      setRecoveryCodes(recovery_codes)
      reset()
      toast.success(t("totpCard.nouveauxCodesDeSecoursGeneres"))
      load()
    })
  }

  const copyCodes = async () => {
    if (!recoveryCodes) return
    try {
      await navigator.clipboard.writeText(recoveryCodes.join("\n"))
      toast.success(t("totpCard.codesCopies"))
    } catch {
      toast.error(t("totpCard.copieImpossible"))
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
      <Label htmlFor="totp-settings-password">{t("totpCard.motDePasseActuel")}</Label>
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
        {busy ? t("totpCard.enCours") : submitLabel}
      </Button>
      <Button type="button" variant="ghost" onClick={reset} disabled={busy} className="h-11 sm:h-10">
        {t("totpCard.annuler")}
      </Button>
    </div>
  )

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <ShieldCheck className="h-5 w-5" />
          {t("totpCard.doubleAuthentification")}
          {status?.enabled && <Badge variant="secondary">{t("totpCard.activee")}</Badge>}
        </CardTitle>
        <CardDescription>
          {t("totpCard.unCodeDeGoogleAuthenticator")}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {recoveryCodes && (
          <div className="space-y-3 rounded-lg border border-amber-500/40 bg-amber-500/5 p-4" data-privacy-ignore>
            <p className="text-sm font-semibold">{t("totpCard.codesDeSecours")}</p>
            <p className="text-sm text-muted-foreground">
              {t("totpCard.gardeLesEnLieuSur")}
            </p>
            <div className="grid grid-cols-2 gap-2 font-mono text-sm">
              {recoveryCodes.map((c) => (
                <span key={c} className="rounded bg-muted px-2 py-1 text-center">{c}</span>
              ))}
            </div>
            <div className="flex flex-col gap-2 sm:flex-row">
              <Button type="button" variant="outline" onClick={copyCodes} className="h-11 sm:h-10">
                <Copy className="mr-2 h-4 w-4" />
                {t("totpCard.copier")}
              </Button>
              <Button type="button" variant="ghost" onClick={() => setRecoveryCodes(null)} className="h-11 sm:h-10">
                {t("totpCard.jeLesAiNotes")}
              </Button>
            </div>
          </div>
        )}

        {step === "idle" && status && !status.enabled && (
          <Button type="button" variant="outline" onClick={() => setStep("password")} className="h-11 w-full sm:w-auto">
            <ShieldCheck className="mr-2 h-4 w-4" />
            {t("totpCard.activer")}
          </Button>
        )}

        {step === "idle" && status?.enabled && (
          <div className="space-y-3">
            <p className="text-sm text-muted-foreground">
              {t("misc.recoveryLeft", { count: status.recovery_codes_left })}
            </p>
            <div className="flex flex-col gap-2 sm:flex-row">
              <Button type="button" variant="outline" onClick={() => setStep("regenerate")} className="h-11 sm:h-10">
                <KeyRound className="mr-2 h-4 w-4" />
                {t("totpCard.nouveauxCodesDeSecours")}
              </Button>
              <Button type="button" variant="ghost" onClick={() => setStep("disable")} className="h-11 text-destructive sm:h-10">
                {t("totpCard.desactiver")}
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
              {t("totpCard.scanneCeQrCodeAvec")}
            </p>
            <img src={setup.qr_svg} alt={t("totpCard.qrCodeDeConfiguration")} className="h-48 w-48 rounded-lg bg-white p-1" />
            <div className="space-y-1">
              <p className="text-xs text-muted-foreground">{t("totpCard.ouSaisisCetteCleA")}</p>
              <p className="break-all font-mono text-sm">{setup.secret.match(/.{1,4}/g)?.join(" ")}</p>
            </div>
            {codeField(t("misc.code6"))}
            {actions("Activer")}
          </form>
        )}

        {step === "disable" && (
          <form onSubmit={disable} className="space-y-3">
            {passwordField}
            {codeField(t("misc.codeAppOrBackup"))}
            {actions(t("misc.disable"))}
          </form>
        )}

        {step === "regenerate" && (
          <form onSubmit={regenerate} className="space-y-3">
            <p className="text-sm text-muted-foreground">{t("totpCard.lesAnciensCodesDeSecours")}</p>
            {codeField(t("misc.codeApp"))}
            {actions(t("misc.generate"))}
          </form>
        )}
      </CardContent>
    </Card>
  )
}
