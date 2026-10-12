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
      <Button type="button" variant="outline" size="sm" className="shrink-0 h-8 w-8 p-0" onClick={copy} aria-label={`Copier ${label}`}>
        {copied ? <Check className="h-4 w-4 text-emerald-600" /> : <Copy className="h-4 w-4" />}
      </Button>
    </div>
  )
}

/** Accès des agents IA (Claude Code) au serveur MCP, par tokens générés ici et révocables. */
export function McpAccessCard() {
  const { profile, refreshProfile } = useAuth()
  const [enabled, setEnabled] = useState(true)
  const [tokens, setTokens] = useState<McpToken[] | null>(null)
  const [name, setName] = useState("Claude Code")
  const [creating, setCreating] = useState(false)
  const [created, setCreated] = useState<McpTokenCreated | null>(null)
  const [toRevoke, setToRevoke] = useState<McpToken | null>(null)

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
    if (!name.trim()) return
    setCreating(true)
    try {
      const token = await api.post<McpTokenCreated>("/admin/mcp-tokens", { name: name.trim() })
      setCreated(token)
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

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Bot className="h-5 w-5" />
          Claude Code (MCP)
        </CardTitle>
        <CardDescription>
          Donnez à Claude Code l'accès à vos données via le serveur MCP. Chaque token est révocable ; aucun ne
          permet de modifier votre profil, votre mot de passe ou de vider la base.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="flex items-center justify-between gap-4">
          <div className="space-y-0.5">
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
              placeholder="Ex. Claude Code — MacBook"
              maxLength={100}
            />
            <Button type="submit" disabled={creating || !name.trim()} className="gap-2 shrink-0">
              <KeyRound className="h-4 w-4" />
              {creating ? "Génération..." : "Générer un token"}
            </Button>
          </div>
        </form>

        {created && (
          <div className="rounded-md border border-amber-200 bg-amber-50 dark:bg-amber-950/30 dark:border-amber-900 p-4 space-y-3">
            <p className="flex items-center gap-2 text-sm font-semibold text-amber-900 dark:text-amber-200">
              <TriangleAlert className="h-4 w-4" />
              Copiez-le maintenant : ce token ne sera plus affiché.
            </p>
            <div className="space-y-1.5">
              <p className="text-xs font-medium text-slate-700 dark:text-slate-300">
                Dans un terminal, ajoutez Numera à Claude Code :
              </p>
              <CopyBlock value={command} label="Commande" />
            </div>
            <div className="space-y-1.5">
              <p className="text-xs font-medium text-slate-700 dark:text-slate-300">Token seul :</p>
              <CopyBlock value={created.token} label="Token" />
            </div>
            <p className="text-xs text-slate-600 dark:text-slate-400">
              Vérifiez ensuite avec <code>claude mcp list</code>. Le serveur est joignable sur <code>{mcpUrl}</code>.
            </p>
            <Button type="button" variant="outline" size="sm" onClick={() => setCreated(null)}>
              J'ai copié le token
            </Button>
          </div>
        )}

        <div className="border-t pt-4 space-y-2">
          <Label className="text-sm font-semibold">Tokens actifs</Label>
          {tokens === null ? (
            <Skeleton className="h-12 w-full" />
          ) : tokens.length === 0 ? (
            <p className="text-sm text-slate-500 py-2">Aucun token : générez-en un pour connecter Claude Code.</p>
          ) : (
            <ul className="divide-y rounded-md border">
              {tokens.map((token) => (
                <li key={token.id} className="flex items-center justify-between gap-3 p-3">
                  <div className="min-w-0">
                    <p className="text-sm font-medium truncate">{token.name}</p>
                    <p className="text-xs text-slate-500">
                      <code>{token.token_prefix}…</code> · créé le {formatDateTime(token.created_at)} · dernière
                      utilisation : {formatDateTime(token.last_used_at)}
                    </p>
                  </div>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="shrink-0 text-rose-600 hover:text-rose-700 hover:bg-rose-50"
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
            <Button variant="outline" onClick={() => setToRevoke(null)}>Annuler</Button>
            <Button variant="destructive" onClick={revokeToken}>Révoquer</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Card>
  )
}
