import { useState, useEffect } from "react"
import { User, Lock, Camera, Save, Zap, ZapOff, AlertTriangle } from "lucide-react"
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
          <CardContent className="flex items-center justify-between">
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
