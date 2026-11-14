import i18n from "i18next"
import { useTranslation } from "react-i18next"
import { useState, useEffect } from "react"
import { User, Lock, Camera, Save, AlertTriangle } from "lucide-react"
import { useAuth } from "@/providers/AuthProvider"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { toast } from "sonner"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { putAdminProfile } from "@/lib/api/settings"

type ProfilePayload = {
  username?: string
  password?: string
  current_password?: string
  profile_picture_url?: string
}

// Changer l'identifiant ou le mot de passe exige le mot de passe actuel et déconnecte
function useProfileUpdate() {
  const { refreshProfile } = useAuth()
  const [loading, setLoading] = useState(false)

  const update = async (payload: ProfilePayload, critical: boolean): Promise<boolean> => {
    setLoading(true)
    try {
      await putAdminProfile(payload)
      toast.success(i18n.t("profileForm.profilMisAJour", { ns: "settings" }))
      if (critical) toast.info(i18n.t("profileForm.deconnexionEnCoursSuiteAu", { ns: "settings" }))
      await refreshProfile()
      return true
    } catch (error) {
      toast.error(error instanceof Error && error.message ? error.message : i18n.t("profileForm.erreurLorsDeLaMise", { ns: "settings" }))
      console.error(error)
      return false
    } finally {
      setLoading(false)
    }
  }

  return { loading, update }
}

function LogoutConfirmDialog({
  open,
  onOpenChange,
  onConfirm,
  loading,
  what,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  onConfirm: () => void
  loading: boolean
  what: string
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-amber-500" />
            {i18n.t("profileForm.confirmationDeModification", { ns: "settings" })}
          </DialogTitle>
          <DialogDescription className="py-2">
            {i18n.t("profileForm.tuEsSurLePoint", { ns: "settings" })} <strong>{what}</strong>.
            <br /><br />
            {i18n.t("profileForm.cetteActionEntraineraUne", { ns: "settings" })} <strong>{i18n.t("profileForm.deconnexionImmediate", { ns: "settings" })}</strong>{i18n.t("profileForm.tuDevrasTeReconnecterAvec", { ns: "settings" })}
            <br /><br />
            {i18n.t("profileForm.continuer", { ns: "settings" })}
          </DialogDescription>
        </DialogHeader>
        <DialogFooter className="gap-2 sm:gap-0">
          <Button variant="outline" className="h-11 sm:h-10" onClick={() => onOpenChange(false)} disabled={loading}>
            {i18n.t("profileForm.annuler", { ns: "settings" })}
          </Button>
          <Button onClick={onConfirm} disabled={loading} className="h-11 sm:h-10 bg-amber-600 hover:bg-amber-700 text-white">
            {i18n.t("profileForm.confirmerEtSeDeconnecter", { ns: "settings" })}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

function SaveButton({ loading }: { loading: boolean }) {
  return (
    <div className="flex justify-end">
      <Button type="submit" disabled={loading} className="h-11 w-full sm:h-10 sm:w-auto bg-slate-900 hover:bg-slate-800 text-white gap-2">
        <Save className="h-4 w-4" />
        {loading ? i18n.t("profileForm.enregistrement", { ns: "settings" }) : i18n.t("profileForm.enregistrer", { ns: "settings" })}
      </Button>
    </div>
  )
}

/** Identifiant et photo (onglet Général). */
export function ProfileInfoCard() {
  const { t } = useTranslation("settings")
  const { profile } = useAuth()
  const { loading, update } = useProfileUpdate()
  const [showConfirmDialog, setShowConfirmDialog] = useState(false)
  const [username, setUsername] = useState("")
  const [profilePictureUrl, setProfilePictureUrl] = useState("")
  const [currentPassword, setCurrentPassword] = useState("")

  useEffect(() => {
    if (profile) {
      setUsername(profile.username)
      setProfilePictureUrl(profile.profile_picture_url || "")
    }
  }, [profile])

  const isUsernameChanged = !!profile && username !== profile.username

  const save = async () => {
    setShowConfirmDialog(false)
    const ok = await update(
      {
        // Chaîne vide acceptée : c'est ainsi qu'on retire la photo
        profile_picture_url: profilePictureUrl,
        ...(isUsernameChanged ? { username, current_password: currentPassword } : {}),
      },
      isUsernameChanged,
    )
    if (ok) setCurrentPassword("")
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!isUsernameChanged) return void save()
    if (!currentPassword) {
      toast.error(t("profileForm.saisisTonMotDePasse"))
      return
    }
    setShowConfirmDialog(true)
  }

  return (
    <>
      <form onSubmit={handleSubmit}>
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <User className="h-5 w-5" />
              {t("profileForm.informationsDuProfil")}
            </CardTitle>
            <CardDescription>{t("profileForm.tonIdentifiantEtTaPhoto")}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex flex-col md:flex-row gap-6 items-center md:items-start">
              <div className="flex flex-col items-center gap-2">
                <div className="h-20 w-20 md:h-24 md:w-24 rounded-full bg-slate-100 flex items-center justify-center overflow-hidden border-2 border-slate-200">
                  {profilePictureUrl ? (
                    <img src={profilePictureUrl} alt={t("profileForm.profil")} className="h-full w-full object-cover" />
                  ) : (
                    <User className="h-12 w-12 text-slate-400" />
                  )}
                </div>
                <Label htmlFor="avatar-url" className="py-2 text-xs cursor-pointer text-slate-500 hover:text-slate-900 flex items-center gap-1">
                  <Camera className="h-3 w-3" /> {t("profileForm.changerLaPhoto")}
                </Label>
              </div>

              <div className="flex-1 space-y-4 w-full">
                <div className="grid gap-2">
                  <Label htmlFor="username">{t("profileForm.nomDUtilisateur")}</Label>
                  <Input
                    id="username"
                    autoCapitalize="none"
                    autoComplete="username"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    placeholder="admin"
                    required
                  />
                </div>
                {isUsernameChanged && (
                  <div className="grid gap-2">
                    <Label htmlFor="profile-current-password">{t("profileForm.motDePasseActuel")}</Label>
                    <Input
                      id="profile-current-password"
                      type="password"
                      autoComplete="current-password"
                      value={currentPassword}
                      onChange={(e) => setCurrentPassword(e.target.value)}
                      placeholder={t("profileForm.requisPourChangerDIdentifiant")}
                    />
                  </div>
                )}
                <div className="grid gap-2">
                  <Label htmlFor="avatar-url">{t("profileForm.urlDeLaPhotoDe")}</Label>
                  <Input
                    id="avatar-url"
                    value={profilePictureUrl}
                    onChange={(e) => setProfilePictureUrl(e.target.value)}
                    placeholder="https://..."
                  />
                </div>
              </div>
            </div>
            <SaveButton loading={loading} />
          </CardContent>
        </Card>
      </form>

      <LogoutConfirmDialog
        open={showConfirmDialog}
        onOpenChange={setShowConfirmDialog}
        onConfirm={save}
        loading={loading}
        what={t("misc.whatUsername")}
      />
    </>
  )
}

/** Changement de mot de passe (onglet Sécurité). */
export function PasswordCard() {
  const { t } = useTranslation("settings")
  const { loading, update } = useProfileUpdate()
  const [showConfirmDialog, setShowConfirmDialog] = useState(false)
  const [currentPassword, setCurrentPassword] = useState("")
  const [password, setPassword] = useState("")
  const [confirmPassword, setConfirmPassword] = useState("")

  const save = async () => {
    setShowConfirmDialog(false)
    const ok = await update({ password, current_password: currentPassword }, true)
    if (ok) {
      setCurrentPassword("")
      setPassword("")
      setConfirmPassword("")
    }
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (password !== confirmPassword) {
      toast.error(t("profileForm.lesMotsDePasseNe"))
      return
    }
    if (password.length < 8) {
      toast.error(t("profileForm.leMotDePasseDoit"))
      return
    }
    if (!currentPassword) {
      toast.error(t("profileForm.saisisTonMotDePasse2"))
      return
    }
    setShowConfirmDialog(true)
  }

  return (
    <>
      <form onSubmit={handleSubmit}>
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Lock className="h-5 w-5" />
              {t("profileForm.motDePasse")}
            </CardTitle>
            <CardDescription>{t("profileForm.auMoins8CaracteresTu")}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Identifiant caché : aide le gestionnaire de mots de passe à rattacher le nouveau mot de passe */}
            <input type="text" name="username" autoComplete="username" className="hidden" readOnly />
            <div className="grid gap-2">
              <Label htmlFor="current-password">{t("profileForm.motDePasseActuel")}</Label>
              <Input
                id="current-password"
                type="password"
                autoComplete="current-password"
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
              />
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="grid gap-2">
                <Label htmlFor="new-password">{t("profileForm.nouveauMotDePasse")}</Label>
                <Input
                  id="new-password"
                  autoComplete="new-password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  required
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="confirm-password">{t("profileForm.confirmerLeMotDePasse")}</Label>
                <Input
                  id="confirm-password"
                  autoComplete="new-password"
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="••••••••"
                  required
                />
              </div>
            </div>
            <SaveButton loading={loading} />
          </CardContent>
        </Card>
      </form>

      <LogoutConfirmDialog
        open={showConfirmDialog}
        onOpenChange={setShowConfirmDialog}
        onConfirm={save}
        loading={loading}
        what={t("misc.whatPassword")}
      />
    </>
  )
}
