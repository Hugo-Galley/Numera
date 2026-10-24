import { useCallback, useEffect, useState } from "react"
import { Bot, Check, Copy, KeyRound, Trash2, TriangleAlert } from "lucide-react"
import { toast } from "sonner"
import { useAuth } from "@/providers/AuthProvider"
import { api } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { Skeleton } from "@/components/ui/skeleton"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"

interface McpToken {
  id: number
  name: string
  token_prefix: string
  created_at: string
  last_used_at: string | null
}

interface McpTokenCreated extends McpToken {
  token: string
}

type McpClient = "claude-code" | "claude-desktop"

const CLIENTS: { id: McpClient; label: string }[] = [
  { id: "claude-code", label: "Claude Code" },
  { id: "claude-desktop", label: "Claude Desktop" },
]

const formatDateTime = (value: string | null) =>
  value
    ? new Date(`${value}Z`).toLocaleString("fr-FR", { dateStyle: "short", timeStyle: "short" })
    : "Jamais"

function CopyBlock({ value, label }: { value: string; label: string }) {
  const [copied, setCopied] = useState(false)
  const copy = async () => {
    await navigator.clipboard.writeText(value)
    setCopied(true)
    toast.success(`${label} copié`)
    setTimeout(() => setCopied(false), 2000)
  }
  return (
    <div className="flex items-start gap-2">
      <pre className="flex-1 min-w-0 p-2.5 bg-slate-900 text-slate-100 rounded overflow-x-auto text-[11px] leading-relaxed font-mono whitespace-pre-wrap break-all">
        {value}
      </pre>
      <Button type="button" variant="outline" size="sm" className="shrink-0 h-10 w-10 p-0 sm:h-8 sm:w-8" onClick={copy} aria-label={`Copier ${label}`}>
        {copied ? <Check className="h-4 w-4 text-emerald-600" /> : <Copy className="h-4 w-4" />}
      </Button>
    </div>
  )
}

/** Accès en lecture seule de Claude (Code / Desktop) au serveur MCP, par tokens générés ici et révocables. */
export function McpAccessCard() {
  const { profile, refreshProfile } = useAuth()
  const [enabled, setEnabled] = useState(true)
  const [tokens, setTokens] = useState<McpToken[] | null>(null)
  const [name, setName] = useState("Claude Code")
  const [password, setPassword] = useState("")
  const [creating, setCreating] = useState(false)
  const [created, setCreated] = useState<McpTokenCreated | null>(null)
  const [toRevoke, setToRevoke] = useState<McpToken | null>(null)
  const [client, setClient] = useState<McpClient>("claude-code")

  const mcpUrl = `${window.location.origin}/mcp`

  const loadTokens = useCallback(async () => {
    try {
      setTokens(await api.get<McpToken[]>("/admin/mcp-tokens"))
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Impossible de charger les tokens MCP")
      setTokens([])
    }
  }, [])

  useEffect(() => {
    loadTokens()
  }, [loadTokens])

  useEffect(() => {
    if (profile) setEnabled(profile.mcp_enabled)
  }, [profile])

  const toggleAccess = async (value: boolean) => {
    setEnabled(value)
    try {
      await api.put("/admin/profile", { mcp_enabled: value })
      toast.success(value ? "Accès MCP activé" : "Accès MCP coupé : tous les tokens sont refusés")
      await refreshProfile()
    } catch (error) {
      setEnabled(!value)
      toast.error(error instanceof Error ? error.message : "Erreur lors de la mise à jour")
    }
  }

  const createToken = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim() || !password) return
    setCreating(true)
    try {
      const token = await api.post<McpTokenCreated>("/admin/mcp-tokens", { name: name.trim(), current_password: password })
      setCreated(token)
      setPassword("")
      setClient(name.toLowerCase().includes("desktop") ? "claude-desktop" : "claude-code")
      await loadTokens()
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Impossible de générer le token")
    } finally {
      setCreating(false)
    }
  }

  const revokeToken = async () => {
    if (!toRevoke) return
    try {
      await api.delete(`/admin/mcp-tokens/${toRevoke.id}`)
      toast.success(`Token « ${toRevoke.name} » révoqué`)
      if (created?.id === toRevoke.id) setCreated(null)
      await loadTokens()
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Impossible de révoquer le token")
    } finally {
      setToRevoke(null)
    }
  }

  const command = created
    ? `claude mcp add --transport http --scope user numera ${mcpUrl} --header "Authorization: Bearer ${created.token}"`
    : ""
  // Claude Desktop ne passe pas d'en-tête aux serveurs distants : pont local mcp-remote (Node.js requis)
  const desktopConfig = created
    ? JSON.stringify(
        {
          mcpServers: {
            numera: {
              command: "npx",
              args: ["-y", "mcp-remote", mcpUrl, "--header", "Authorization:${NUMERA_AUTH}"],
              env: { NUMERA_AUTH: `Bearer ${created.token}` },
            },
          },
        },
        null,
        2,
      )
    : ""

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Bot className="h-5 w-5" />
          Claude (MCP)
        </CardTitle>
        <CardDescription>
          Donnez à Claude Code ou Claude Desktop un accès en <strong>lecture seule</strong> à vos données via le
          serveur MCP. Chaque token est révocable ; aucun ne permet de modifier quoi que ce soit.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="flex items-center justify-between gap-4">
          <div className="min-w-0 space-y-0.5">
            <Label className="text-base">Accès MCP</Label>
            <p className="text-sm text-slate-500">
              Désactivé, tous les tokens sont refusés immédiatement (sans les supprimer).
            </p>
          </div>
          <Switch checked={enabled} onCheckedChange={toggleAccess} />
        </div>

        <form onSubmit={createToken} className="border-t pt-4 space-y-2">
          <Label htmlFor="mcp-token-name" className="text-sm font-semibold">Nouveau token</Label>
          <div className="flex flex-col sm:flex-row gap-2">
            <Input
              id="mcp-token-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Ex. Claude Desktop — MacBook"
              maxLength={100}
            />
            <Button type="submit" disabled={creating || !name.trim() || !password} className="h-11 gap-2 shrink-0 sm:h-10">
              <KeyRound className="h-4 w-4" />
              {creating ? "Génération..." : "Générer un token"}
            </Button>
          </div>
          <Input
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Mot de passe actuel (requis)"
            aria-label="Mot de passe actuel"
          />
        </form>

        {created && (
          <div className="rounded-md border border-amber-200 bg-amber-50 dark:bg-amber-950/30 dark:border-amber-900 p-4 space-y-3">
            <p className="flex items-center gap-2 text-sm font-semibold text-amber-900 dark:text-amber-200">
              <TriangleAlert className="h-4 w-4" />
              Copiez-le maintenant : ce token ne sera plus affiché.
            </p>
            <div className="flex flex-wrap gap-2">
              {CLIENTS.map((item) => (
                <Button
                  key={item.id}
                  type="button"
                  size="sm"
                  variant={client === item.id ? "default" : "outline"}
                  onClick={() => setClient(item.id)}
                  className="h-10 text-xs sm:h-9"
                >
                  {item.label}
                </Button>
              ))}
            </div>
            {client === "claude-code" ? (
              <div className="space-y-1.5">
                <p className="text-xs font-medium text-slate-700 dark:text-slate-300">
                  Dans un terminal, ajoutez Numera à Claude Code :
                </p>
                <CopyBlock value={command} label="Commande" />
                <p className="text-xs text-slate-600 dark:text-slate-400">
                  Vérifiez ensuite avec <code>claude mcp list</code>.
                </p>
              </div>
            ) : (
              <div className="space-y-1.5">
                <p className="text-xs font-medium text-slate-700 dark:text-slate-300">
                  Claude Desktop → Réglages → Développeur → Modifier la configuration, puis fusionnez ce bloc dans{" "}
                  <code>claude_desktop_config.json</code> :
                </p>
                <CopyBlock value={desktopConfig} label="Configuration" />
                <p className="text-xs text-slate-600 dark:text-slate-400">
                  Node.js doit être installé (le pont <code>mcp-remote</code> transmet le token). Redémarrez ensuite
                  Claude Desktop.
                </p>
              </div>
            )}
            <div className="space-y-1.5">
              <p className="text-xs font-medium text-slate-700 dark:text-slate-300">Token seul :</p>
              <CopyBlock value={created.token} label="Token" />
            </div>
            <p className="text-xs text-slate-600 dark:text-slate-400">
              Serveur MCP : <code>{mcpUrl}</code>
            </p>
            <Button type="button" variant="outline" className="h-11 w-full sm:h-9 sm:w-auto" onClick={() => setCreated(null)}>
              J'ai copié le token
            </Button>
          </div>
        )}

        <div className="border-t pt-4 space-y-2">
          <Label className="text-sm font-semibold">Tokens actifs</Label>
          {tokens === null ? (
            <Skeleton className="h-12 w-full" />
          ) : tokens.length === 0 ? (
            <p className="text-sm text-slate-500 py-2">Aucun token : générez-en un pour connecter Claude.</p>
          ) : (
            <ul className="divide-y rounded-md border">
              {tokens.map((token) => (
                <li key={token.id} className="flex items-center justify-between gap-3 p-3">
                  <div className="min-w-0">
                    <p className="text-sm font-medium truncate">{token.name}</p>
                    <p className="text-xs text-slate-500">
                      <code>{token.token_prefix}…</code> · créé le {formatDateTime(token.created_at)}
                      <span className="block sm:inline"><span className="hidden sm:inline"> · </span>dernière utilisation : {formatDateTime(token.last_used_at)}</span>
                    </p>
                  </div>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="h-10 w-10 shrink-0 p-0 text-rose-600 hover:text-rose-700 hover:bg-rose-50"
                    onClick={() => setToRevoke(token)}
                    aria-label={`Révoquer ${token.name}`}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </CardContent>

      <Dialog open={toRevoke !== null} onOpenChange={(open) => !open && setToRevoke(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Révoquer « {toRevoke?.name} » ?</DialogTitle>
            <DialogDescription>
              Les clients qui utilisent ce token perdent l'accès immédiatement. Cette action est définitive.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="gap-2 sm:gap-0">
            <Button variant="outline" className="h-11 sm:h-10" onClick={() => setToRevoke(null)}>Annuler</Button>
            <Button variant="destructive" className="h-11 sm:h-10" onClick={revokeToken}>Révoquer</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Card>
  )
}
