import { useEffect, useState } from "react"
import { useNavigate, useLocation } from "react-router-dom"
import { useAuth } from "@/providers/AuthProvider"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from "@/components/ui/card"
import { Label } from "@/components/ui/label"
import { API_BASE } from "@/lib/api"
import { toast } from "sonner"
import { Fingerprint } from "lucide-react"
import { loginWithPasskey, passkeySupported } from "@/lib/passkey"

export default function Login() {
  const [username, setUsername] = useState("")
  const [password, setPassword] = useState("")
  const [loading, setLoading] = useState(false)
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  const from = (location.state as any)?.from?.pathname || "/"
  const [passkeyAvailable, setPasskeyAvailable] = useState(false)

  useEffect(() => {
    if (!passkeySupported()) return
    fetch(`${API_BASE}/auth/passkey/available`)
      .then((r) => (r.ok ? r.json() : { available: false }))
      .then((d) => setPasskeyAvailable(!!d.available))
      .catch(() => {})
  }, [])

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
        const error = await response.json()
        throw new Error(error.detail || "Identifiants incorrects")
      }

      const data = await response.json()
      login(data.access_token)
      toast.success("Connexion réussie")
      navigate(from, { replace: true })
    } catch (err: any) {
      toast.error(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-dvh items-start justify-center bg-muted/40 px-4 pb-8 pt-[12dvh] sm:items-center sm:py-4">
      <Card className="w-full max-w-sm">
        <CardHeader className="space-y-1 text-center">
          <CardTitle className="text-3xl font-bold sm:text-2xl">Numera</CardTitle>
          <p className="text-sm text-muted-foreground">
            Entrez vos identifiants pour vous connecter
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
                className="h-12 text-base sm:h-10 sm:text-sm"
                placeholder="admin"
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
                className="h-12 text-base sm:h-10 sm:text-sm"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>
          </CardContent>
          <CardFooter className="flex-col gap-3">
            <Button className="h-12 w-full text-base sm:h-10 sm:text-sm" type="submit" disabled={loading}>
              {loading ? "Connexion..." : "Se connecter"}
            </Button>
            {passkeyAvailable && (
              <Button type="button" variant="outline" className="h-12 w-full text-base sm:h-10 sm:text-sm" onClick={handlePasskey} disabled={loading}>
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
