import { useEffect, useState } from "react"
import { Navigate, useNavigate, useLocation, useSearchParams } from "react-router-dom"
import { useAuth } from "@/providers/AuthProvider"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from "@/components/ui/card"
import { Label } from "@/components/ui/label"
import { API_BASE } from "@/lib/api"
import { toast } from "sonner"
import { Fingerprint, ShieldCheck } from "lucide-react"
import { loginWithPasskey, passkeySupported } from "@/lib/passkey"

export default function Login() {
  const [username, setUsername] = useState("")
  const [password, setPassword] = useState("")
  const [loading, setLoading] = useState(false)
  // Double authentification : jeton intermédiaire reçu après un mot de passe correct
  const [mfaToken, setMfaToken] = useState<string | null>(null)
  const [code, setCode] = useState("")
  const { login, isAuthenticated } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [searchParams] = useSearchParams()

  // Retour après connexion : état du routeur (ProtectedRoute) ou ?from= (session expirée en cours de route).
  // Seuls les chemins internes sont acceptés (pas de redirection vers un site externe).
  const stateFrom = (location.state as any)?.from
  const queryFrom = searchParams.get("from")
  const candidate = stateFrom ? `${stateFrom.pathname}${stateFrom.search || ""}` : queryFrom
  const from = candidate && candidate.startsWith("/") && !candidate.startsWith("//") && !candidate.startsWith("/login") ? candidate : "/"
  const [passkeyAvailable, setPasskeyAvailable] = useState(false)

  useEffect(() => {
    if (!passkeySupported()) return
    fetch(`${API_BASE}/auth/passkey/available`)
      .then((r) => (r.ok ? r.json() : { available: false }))
      .then((d) => setPasskeyAvailable(!!d.available))
      .catch(() => {})
  }, [])

  if (isAuthenticated) return <Navigate to={from} replace />

  const handlePasskey = async () => {
    setLoading(true)
    try {
      login(await loginWithPasskey())
      toast.success("Connexion réussie")
      navigate(from, { replace: true })
    } catch (err: any) {
      if (err?.name !== "NotAllowedError") toast.error(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)

    try {
      const params = new URLSearchParams()
      params.append("username", username)
      params.append("password", password)

      const response = await fetch(`${API_BASE}/auth/token`, {
        method: "POST",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
        },
        body: params,
      })

      if (!response.ok) {
        const error = await response.json().catch(() => null)
        const detail = error?.detail
        if (response.status === 429) throw new Error("Trop de tentatives. Réessaie dans quelques minutes.")
        throw new Error(typeof detail === "string" && detail ? detail : "Identifiants incorrects")
      }

      const data = await response.json()
      if (data.mfa_required) {
        setMfaToken(data.mfa_token)
        setCode("")
        return
      }
      login(data.access_token)
      toast.success("Connexion réussie")
      navigate(from, { replace: true })
    } catch (err: any) {
      toast.error(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleCode = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    try {
      const response = await fetch(`${API_BASE}/auth/totp/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mfa_token: mfaToken, code }),
      })
      if (!response.ok) {
        const detail = (await response.json().catch(() => null))?.detail
        if (response.status === 429) throw new Error("Trop de tentatives. Réessaie dans quelques minutes.")
        if (typeof detail === "string" && detail.startsWith("Étape de connexion")) setMfaToken(null)
        throw new Error(typeof detail === "string" && detail ? detail : "Code incorrect")
      }
      login((await response.json()).access_token)
      toast.success("Connexion réussie")
      navigate(from, { replace: true })
    } catch (err: any) {
      setCode("")
      toast.error(err.message)
    } finally {
      setLoading(false)
    }
  }

  if (mfaToken) {
    return (
      <div className="flex min-h-dvh items-start justify-center bg-muted/40 px-4 pb-8 pt-[12dvh] sm:items-center sm:py-4">
        <Card className="w-full max-w-sm">
          <CardHeader className="space-y-1 text-center">
            <ShieldCheck className="mx-auto h-8 w-8 text-primary" />
            <CardTitle className="text-2xl font-bold">Vérification</CardTitle>
            <p className="text-sm text-muted-foreground">
              Saisis le code à 6 chiffres de ton application d'authentification, ou un code de secours.
            </p>
          </CardHeader>
          <form onSubmit={handleCode}>
            <CardContent>
              <Label htmlFor="totp-code" className="sr-only">Code</Label>
              <Input
                id="totp-code"
                autoFocus
                inputMode="text"
                autoComplete="one-time-code"
                autoCapitalize="none"
                autoCorrect="off"
                placeholder="123456"
                className="h-12 text-center font-mono text-lg tracking-[0.3em] sm:h-11"
                value={code}
                onChange={(e) => setCode(e.target.value)}
                required
              />
            </CardContent>
            <CardFooter className="flex-col gap-3">
              <Button className="h-12 w-full text-base sm:h-10 lg:text-sm" type="submit" disabled={loading || !code.trim()}>
                {loading ? "Vérification..." : "Valider"}
              </Button>
              <Button type="button" variant="ghost" className="h-11 w-full" onClick={() => setMfaToken(null)} disabled={loading}>
                Retour
              </Button>
            </CardFooter>
          </form>
        </Card>
      </div>
    )
  }

  return (
    <div className="flex min-h-dvh items-start justify-center bg-muted/40 px-4 pb-8 pt-[12dvh] sm:items-center sm:py-4">
      <Card className="w-full max-w-sm">
        <CardHeader className="space-y-1 text-center">
          <CardTitle className="text-3xl font-bold sm:text-2xl">Numera</CardTitle>
          <p className="text-sm text-muted-foreground">
            Saisis tes identifiants pour te connecter
          </p>
        </CardHeader>
        <form onSubmit={handleSubmit}>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="username">Utilisateur</Label>
              <Input
                id="username"
                type="text"
                autoComplete="username"
                autoCapitalize="none"
                autoCorrect="off"
                className="h-12 text-base sm:h-10 lg:text-sm"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Mot de passe</Label>
              <Input
                id="password"
                type="password"
                autoComplete="current-password"
                className="h-12 text-base sm:h-10 lg:text-sm"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>
          </CardContent>
          <CardFooter className="flex-col gap-3">
            <Button className="h-12 w-full text-base sm:h-10 lg:text-sm" type="submit" disabled={loading}>
              {loading ? "Connexion..." : "Se connecter"}
            </Button>
            {passkeyAvailable && (
              <Button type="button" variant="outline" className="h-12 w-full text-base sm:h-10 lg:text-sm" onClick={handlePasskey} disabled={loading}>
                <Fingerprint className="mr-2 h-4 w-4" />
                Face ID / Touch ID
              </Button>
            )}
          </CardFooter>
        </form>
      </Card>
    </div>
  )
}
