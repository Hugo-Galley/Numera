import { useState, useEffect } from "react"
import { User, Lock, Camera, Save, Zap, ZapOff, AlertTriangle, Check, Copy, Terminal, Loader2 } from "lucide-react"
import { useAuth } from "@/providers/AuthProvider"
import { api } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Switch } from "@/components/ui/switch"
import { toast } from "sonner"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"

export function AccountTab() {
  const { profile, refreshProfile } = useAuth()
  const [loading, setLoading] = useState(false)
  const [showConfirmDialog, setShowConfirmDialog] = useState(false)
  
  const [username, setUsername] = useState("")
  const [profilePictureUrl, setProfilePictureUrl] = useState("")
  const [password, setPassword] = useState("")
  const [confirmPassword, setConfirmPassword] = useState("")
  const [mcpEnabled, setMcpEnabled] = useState(true)
  const [selectedClient, setSelectedClient] = useState<string>("")
  const [installing, setInstalling] = useState(false)
  const [installResult, setInstallResult] = useState<{ success: boolean; message: string; config_content?: any } | null>(null)
  const [isRemoteInstance, setIsRemoteInstance] = useState(
    typeof window !== "undefined" && 
    window.location.hostname !== "localhost" && 
    window.location.hostname !== "127.0.0.1"
  )

  const getRemoteMcpConfig = (client: string) => {
    const origin = typeof window !== 'undefined' ? window.location.origin : 'https://votre-vps-url'
    const vpsUrl = origin.endsWith('/') ? `${origin}api` : `${origin}/api`
    return {
      "mcpServers": {
        "numera-mcp": {
          "command": "python3",
          "args": ["/chemin/absolu/vers/votre/dossier/local/mcp-server/server.py"],
          "env": {
            "MCP_MODE": "api",
            "MCP_API_URL": vpsUrl,
            "MCP_API_USERNAME": "admin",
            "MCP_API_PASSWORD": "VOTRE_MOT_DE_PASSE_DE_NUMERA"
          }
        }
      }
    }
  }

  const handleInstallMcp = async () => {
    if (!selectedClient) return
    setInstalling(true)
    setInstallResult(null)
    try {
      const res = await api.post<{ success: boolean; message: string; config_content?: any }>("/admin/mcp/install", { client: selectedClient })
      setInstallResult(res)
      if (res.success) {
        toast.success("Configuration installée avec succès !")
      } else {
        toast.error("Échec de l'écriture automatique.")
      }
    } catch (err: any) {
      toast.error(err.message || "Erreur lors de l'installation.")
      setInstallResult({
        success: false,
        message: err.message || "Erreur inconnue."
      })
    } finally {
      setInstalling(false)
    }
  }

  useEffect(() => {
    if (profile) {
      setUsername(profile.username)
      setProfilePictureUrl(profile.profile_picture_url || "")
      setMcpEnabled(profile.mcp_enabled)
    }
  }, [profile])

  const handleSubmitAttempt = (e: React.FormEvent) => {
    e.preventDefault()
    
    if (password && password !== confirmPassword) {
      toast.error("Les mots de passe ne correspondent pas")
      return
    }

    const isUsernameChanged = username !== profile?.username
    const isPasswordChanged = password.length > 0

    if (isUsernameChanged || isPasswordChanged) {
      setShowConfirmDialog(true)
    } else {
      performUpdate()
    }
  }

  const performUpdate = async () => {
    setLoading(true)
    setShowConfirmDialog(false)
    try {
      await api.put("/admin/profile", {
        username,
        profile_picture_url: profilePictureUrl || null,
        mcp_enabled: mcpEnabled,
        ...(password ? { password } : {})
      })
      
      toast.success("Profil mis à jour avec succès")
      const wasCriticalChange = username !== profile?.username || password.length > 0
      
      setPassword("")
      setConfirmPassword("")
      
      if (wasCriticalChange) {
        toast.info("Déconnexion en cours suite au changement d'identifiants...")
      }
      
      await refreshProfile()
    } catch (error) {
      toast.error("Erreur lors de la mise à jour du profil")
      console.error(error)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      <form onSubmit={handleSubmitAttempt} className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <User className="h-5 w-5" />
              Informations du profil
            </CardTitle>
            <CardDescription>
              Gérez votre identité et votre apparence sur la plateforme.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex flex-col md:flex-row gap-6 items-start">
              <div className="flex flex-col items-center gap-2">
                <div className="h-24 w-24 rounded-full bg-slate-100 flex items-center justify-center overflow-hidden border-2 border-slate-200">
                  {profilePictureUrl ? (
                    <img src={profilePictureUrl} alt="Profil" className="h-full w-full object-cover" />
                  ) : (
                    <User className="h-12 w-12 text-slate-400" />
                  )}
                </div>
                <Label htmlFor="avatar-url" className="text-xs cursor-pointer text-slate-500 hover:text-slate-900 flex items-center gap-1">
                  <Camera className="h-3 w-3" /> Changer la photo
                </Label>
              </div>
              
              <div className="flex-1 space-y-4 w-full">
                <div className="grid gap-2">
                  <Label htmlFor="username">Nom d'utilisateur</Label>
                  <Input 
                    id="username" 
                    value={username} 
                    onChange={(e) => setUsername(e.target.value)} 
                    placeholder="admin"
                    required
                  />
                </div>
                <div className="grid gap-2">
                  <Label htmlFor="avatar-url">URL de la photo de profil</Label>
                  <Input 
                    id="avatar-url" 
                    value={profilePictureUrl} 
                    onChange={(e) => setProfilePictureUrl(e.target.value)} 
                    placeholder="https://..."
                  />
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Lock className="h-5 w-5" />
              Sécurité
            </CardTitle>
            <CardDescription>
              Laissez vide pour conserver le mot de passe actuel.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="grid gap-2">
                <Label htmlFor="new-password">Nouveau mot de passe</Label>
                <Input 
                  id="new-password" 
                  type="password" 
                  value={password} 
                  onChange={(e) => setPassword(e.target.value)} 
                  placeholder="••••••••"
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="confirm-password">Confirmer le mot de passe</Label>
                <Input 
                  id="confirm-password" 
                  type="password" 
                  value={confirmPassword} 
                  onChange={(e) => setConfirmPassword(e.target.value)} 
                  placeholder="••••••••"
                />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              {mcpEnabled ? <Zap className="h-5 w-5 text-amber-500" /> : <ZapOff className="h-5 w-5 text-slate-400" />}
              Serveur MCP
            </CardTitle>
            <CardDescription>
              Le protocole MCP permet aux agents IA (Claude, Cursor) de lire vos données.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label className="text-base">Accès au serveur MCP</Label>
                <p className="text-sm text-slate-500">
                  Activez ou désactivez l'accès externe via le Model Context Protocol.
                </p>
              </div>
              <Switch 
                checked={mcpEnabled} 
                onCheckedChange={setMcpEnabled} 
              />
            </div>
            
            {mcpEnabled && (
              <>
                <div className="flex items-center justify-between border-t pt-4">
                  <div className="space-y-0.5">
                    <Label className="text-sm font-semibold">Instance hébergée à distance (VPS / Docker)</Label>
                    <p className="text-xs text-slate-500">
                      Cochez cette option si l'application s'exécute sur un serveur VPS distant ou dans un conteneur Docker.
                    </p>
                  </div>
                  <Switch 
                    checked={isRemoteInstance} 
                    onCheckedChange={(checked) => {
                      setIsRemoteInstance(checked)
                      setSelectedClient("")
                      setInstallResult(null)
                    }} 
                  />
                </div>

                <div className="mt-4 border-t pt-4 space-y-4">
                  <Label className="text-sm font-semibold text-slate-700 flex items-center gap-2">
                    <Terminal className="h-4 w-4 text-slate-500" />
                    {isRemoteInstance 
                      ? "Configuration pour instance distante (VPS)"
                      : "Installation automatique du Serveur MCP (Mac / Local)"
                    }
                  </Label>
                  <p className="text-xs text-slate-500 leading-relaxed">
                    {isRemoteInstance
                      ? "Comme votre instance est hébergée sur un serveur distant, vous devez copier le dossier `mcp-server` localement sur votre Mac et configurer votre client IA pour pointer vers l'URL de votre VPS."
                      : "Sélectionnez votre éditeur/application IA local(e) pour installer ou mettre à jour automatiquement le serveur MCP de Numera sur votre machine."
                    }
                  </p>
                  
                  <div className="flex flex-wrap gap-2">
                    {[
                      { id: "claude", label: "Claude Desktop" },
                      { id: "cursor", label: "Cursor (Global)" },
                      ...(!isRemoteInstance ? [{ id: "cursor_project", label: "Cursor (Projet)" }] : []),
                      { id: "cline", label: "Cline (VSCode)" },
                      { id: "roo_code", label: "Roo Code (VSCode)" },
                    ].map((item) => (
                      <Button
                        key={item.id}
                        type="button"
                        variant={selectedClient === item.id ? "default" : "outline"}
                        size="sm"
                        onClick={() => {
                          setSelectedClient(item.id)
                          setInstallResult(null)
                        }}
                        className="text-xs"
                      >
                        {item.label}
                      </Button>
                    ))}
                  </div>
                  
                  {selectedClient && (
                    <div className="space-y-2">
                      {!isRemoteInstance ? (
                        <>
                          <Button
                            type="button"
                            size="sm"
                            onClick={handleInstallMcp}
                            disabled={installing}
                            className="bg-amber-600 hover:bg-amber-700 text-white text-xs gap-2"
                          >
                            {installing && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
                            Installer sur {
                              selectedClient === "claude" ? "Claude Desktop" :
                              selectedClient === "cursor" ? "Cursor Global" :
                              selectedClient === "cursor_project" ? "Cursor Projet" :
                              selectedClient === "cline" ? "Cline" : "Roo Code"
                            }
                          </Button>
                          
                          {installResult && (
                            <div className={`p-3 rounded-md text-xs border ${
                              installResult.success 
                                ? "bg-emerald-50 text-emerald-800 border-emerald-200" 
                                : "bg-red-50 text-red-800 border-red-200"
                            }`}>
                              <p className="font-semibold mb-1">{installResult.message}</p>
                              {installResult.config_content && (
                                <div className="mt-3 space-y-2">
                                  <p className="font-medium text-slate-700">Configuration JSON générée :</p>
                                  <pre className="p-2.5 bg-slate-900 text-slate-100 rounded overflow-x-auto text-[10px] leading-relaxed font-mono">
                                    {JSON.stringify(installResult.config_content, null, 2)}
                                  </pre>
                                  <div className="flex gap-2">
                                    <Button
                                      type="button"
                                      variant="outline"
                                      size="sm"
                                      className="text-[11px] h-7 px-2.5 gap-1.5"
                                      onClick={() => {
                                        navigator.clipboard.writeText(JSON.stringify(installResult.config_content, null, 2));
                                        toast.success("Configuration copiée !");
                                      }}
                                    >
                                      <Copy className="h-3.5 w-3.5" />
                                      Copier le JSON
                                    </Button>
                                  </div>
                                </div>
                              )}
                            </div>
                          )}
                        </>
                      ) : (
                        <div className="p-3 rounded-md text-xs border bg-slate-50 border-slate-200 space-y-3">
                          <p className="font-semibold text-slate-800">
                            Instructions pour {
                              selectedClient === "claude" ? "Claude Desktop" :
                              selectedClient === "cursor" ? "Cursor" :
                              selectedClient === "cline" ? "Cline (VSCode)" : "Roo Code (VSCode)"
                            } :
                          </p>
                          <ol className="list-decimal pl-4 space-y-1.5 text-slate-600">
                            <li>Copiez le dossier <code>mcp-server</code> sur votre Mac local.</li>
                            <li>Configurez votre client IA en utilisant le fichier JSON ci-dessous (veillez à remplacer <code>/chemin/absolu/vers/...</code> par le chemin réel du fichier <code>server.py</code> sur votre Mac).</li>
                            <li>Remplacez <code>VOTRE_MOT_DE_PASSE_DE_NUMERA</code> par votre mot de passe administrateur.</li>
                          </ol>
                          <div className="mt-3 space-y-2">
                            <p className="font-medium text-slate-700">Configuration JSON pour instance distante :</p>
                            <pre className="p-2.5 bg-slate-900 text-slate-100 rounded overflow-x-auto text-[10px] leading-relaxed font-mono">
                              {JSON.stringify(getRemoteMcpConfig(selectedClient), null, 2)}
                            </pre>
                            <Button
                              type="button"
                              variant="outline"
                              size="sm"
                              className="text-[11px] h-7 px-2.5 gap-1.5"
                              onClick={() => {
                                navigator.clipboard.writeText(JSON.stringify(getRemoteMcpConfig(selectedClient), null, 2));
                                toast.success("Configuration copiée !");
                              }}
                            >
                              <Copy className="h-3.5 w-3.5" />
                              Copier le JSON distant
                            </Button>
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </>
            )}
          </CardContent>
        </Card>

        <div className="flex justify-end">
          <Button type="submit" disabled={loading} className="bg-slate-900 hover:bg-slate-800 text-white gap-2">
            <Save className="h-4 w-4" />
            {loading ? "Enregistrement..." : "Enregistrer les modifications"}
          </Button>
        </div>
      </form>

      <Dialog open={showConfirmDialog} onOpenChange={setShowConfirmDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-amber-500" />
              Confirmation de modification
            </DialogTitle>
            <DialogDescription className="py-2">
              Vous êtes sur le point de modifier votre <strong>nom d'utilisateur</strong> ou votre <strong>mot de passe</strong>.
              <br /><br />
              Cette action entraînera une <strong>déconnexion immédiate</strong>. Vous devrez vous reconnecter avec vos nouveaux identifiants.
              <br /><br />
              Souhaitez-vous continuer ?
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="gap-2 sm:gap-0">
            <Button variant="outline" onClick={() => setShowConfirmDialog(false)} disabled={loading}>
              Annuler
            </Button>
            <Button onClick={performUpdate} disabled={loading} className="bg-amber-600 hover:bg-amber-700 text-white">
              Confirmer et se déconnecter
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
