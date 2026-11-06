import i18n from "i18next"
import { Trans, useTranslation } from "react-i18next"
import { appLocale } from "@/i18n/locale"
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
    ? new Date(`${value}Z`).toLocaleString(appLocale(), { dateStyle: "short", timeStyle: "short" })
    : i18n.t("misc.neverCap", { ns: "settings" })

function CopyBlock({ value, label }: { value: string; label: string }) {
  const { t } = useTranslation("settings")
  const [copied, setCopied] = useState(false)
  const copy = async () => {
    await navigator.clipboard.writeText(value)
    setCopied(true)
    toast.success(t("misc.copied", { label }))
    setTimeout(() => setCopied(false), 2000)
  }
  return (
    <div className="flex items-start gap-2">
      <pre className="theme-island flex-1 min-w-0 p-2.5 bg-slate-900 text-slate-100 rounded overflow-x-auto text-[11px] leading-relaxed font-mono whitespace-pre-wrap break-all">
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
  const { t } = useTranslation("settings")
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
      toast.error(error instanceof Error ? error.message : t("mcpAccessCard.impossibleDeChargerLesTokens"))
      setTokens([])
    }
  }, [t])

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
      toast.success(value ? t("mcpAccessCard.accesMcpActive") : t("mcpAccessCard.accesMcpCoupeTousLes"))
      await refreshProfile()
    } catch (error) {
      setEnabled(!value)
      toast.error(error instanceof Error ? error.message : t("mcpAccessCard.erreurLorsDeLaMise"))
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
      toast.error(error instanceof Error ? error.message : t("mcpAccessCard.impossibleDeGenererLeToken"))
    } finally {
      setCreating(false)
    }
  }

  const revokeToken = async () => {
    if (!toRevoke) return
    try {
      await api.delete(`/admin/mcp-tokens/${toRevoke.id}`)
      toast.success(t("misc.tokenRevoked", { name: toRevoke.name }))
      if (created?.id === toRevoke.id) setCreated(null)
      await loadTokens()
    } catch (error) {
      toast.error(error instanceof Error ? error.message : t("mcpAccessCard.impossibleDeRevoquerLeToken"))
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
          {t("mcpAccessCard.donnezAClaudeCodeOu")} <strong>{t("mcpAccessCard.lectureSeule")}</strong> {t("misc.mcpIntro")}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="flex items-center justify-between gap-4">
          <div className="min-w-0 space-y-0.5">
            <Label className="text-base">{t("mcpAccessCard.accesMcp")}</Label>
            <p className="text-sm text-slate-500">
              {t("mcpAccessCard.desactiveTousLesTokensSont")}
            </p>
          </div>
          <Switch checked={enabled} onCheckedChange={toggleAccess} />
        </div>

        <form onSubmit={createToken} className="border-t pt-4 space-y-2">
          <Label htmlFor="mcp-token-name" className="text-sm font-semibold">{t("mcpAccessCard.nouveauToken")}</Label>
          <div className="flex flex-col sm:flex-row gap-2">
            <Input
              id="mcp-token-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder={t("mcpAccessCard.exClaudeDesktopMacbook")}
              maxLength={100}
            />
            <Button type="submit" disabled={creating || !name.trim() || !password} className="h-11 gap-2 shrink-0 sm:h-10">
              <KeyRound className="h-4 w-4" />
              {creating ? t("mcpAccessCard.generation") : t("mcpAccessCard.genererUnToken")}
            </Button>
          </div>
          <Input
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder={t("mcpAccessCard.motDePasseActuelRequis")}
            aria-label={t("mcpAccessCard.motDePasseActuel")}
          />
        </form>

        {created && (
          <div className="rounded-md border border-amber-200 bg-amber-50 p-4 space-y-3">
            <p className="flex items-center gap-2 text-sm font-semibold text-amber-900">
              <TriangleAlert className="h-4 w-4" />
              {t("mcpAccessCard.copiezLeMaintenantCeToken")}
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
                <p className="text-xs font-medium text-slate-700">
                  {t("mcpAccessCard.dansUnTerminalAjoutezNumera")}
                </p>
                <CopyBlock value={command} label={t("mcpAccessCard.commande")} />
                <p className="text-xs text-slate-600">
                  {t("mcpAccessCard.verifiezEnsuiteAvec")} <code>claude mcp list</code>.
                </p>
              </div>
            ) : (
              <div className="space-y-1.5">
                <p className="text-xs font-medium text-slate-700">
                  <Trans t={t} i18nKey="misc.desktopSteps" components={{ code: <code /> }} />
                </p>
                <CopyBlock value={desktopConfig} label={t("mcpAccessCard.configuration")} />
                <p className="text-xs text-slate-600">
                  {t("mcpAccessCard.nodeJsDoitEtreInstalle")} <code>mcp-remote</code> {t("mcpAccessCard.transmetLeTokenRedemarrezEnsuite")}
                </p>
              </div>
            )}
            <div className="space-y-1.5">
              <p className="text-xs font-medium text-slate-700">{t("mcpAccessCard.tokenSeul")}</p>
              <CopyBlock value={created.token} label={t("mcpAccessCard.token")} />
            </div>
            <p className="text-xs text-slate-600">
              {t("mcpAccessCard.serveurMcp")} <code>{mcpUrl}</code>
            </p>
            <Button type="button" variant="outline" className="h-11 w-full sm:h-9 sm:w-auto" onClick={() => setCreated(null)}>
              {t("mcpAccessCard.jAiCopieLeToken")}
            </Button>
          </div>
        )}

        <div className="border-t pt-4 space-y-2">
          <Label className="text-sm font-semibold">{t("mcpAccessCard.tokensActifs")}</Label>
          {tokens === null ? (
            <Skeleton className="h-12 w-full" />
          ) : tokens.length === 0 ? (
            <p className="text-sm text-slate-500 py-2">{t("mcpAccessCard.aucunTokenGenerezEnUn")}</p>
          ) : (
            <ul className="divide-y rounded-md border">
              {tokens.map((token) => (
                <li key={token.id} className="flex items-center justify-between gap-3 p-3">
                  <div className="min-w-0">
                    <p className="text-sm font-medium truncate">{token.name}</p>
                    <p className="text-xs text-slate-500">
                      <code>{token.token_prefix}…</code> · {t("misc.createdOn", { date: formatDateTime(token.created_at) })}
                      <span className="block sm:inline"><span className="hidden sm:inline"> · </span>{t("misc.lastUsed", { date: formatDateTime(token.last_used_at) })}</span>
                    </p>
                  </div>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="h-10 w-10 shrink-0 p-0 text-rose-600 hover:text-rose-700 hover:bg-rose-50"
                    onClick={() => setToRevoke(token)}
                    aria-label={t("misc.revokeAria", { name: token.name })}
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
            <DialogTitle>{t("misc.revokeTitle", { name: toRevoke?.name ?? "" })}</DialogTitle>
            <DialogDescription>
              {t("mcpAccessCard.lesClientsQuiUtilisentCe")}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="gap-2 sm:gap-0">
            <Button variant="outline" className="h-11 sm:h-10" onClick={() => setToRevoke(null)}>{t("mcpAccessCard.annuler")}</Button>
            <Button variant="destructive" className="h-11 sm:h-10" onClick={revokeToken}>{t("mcpAccessCard.revoquer")}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Card>
  )
}
