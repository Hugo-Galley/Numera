import { useState } from "react"
import { Layers, Monitor, Moon, Sun } from "lucide-react"
import { toast } from "sonner"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { api } from "@/lib/api"
import { cn, errorMessage } from "@/lib/utils"
import { useAuth } from "@/providers/AuthProvider"
import { type ThemePreference, useUI } from "@/providers/UIProvider"

const THEMES: { value: ThemePreference; label: string; icon: typeof Sun }[] = [
  { value: "light", label: "Clair", icon: Sun },
  { value: "dark", label: "Sombre", icon: Moon },
  { value: "system", label: "Auto", icon: Monitor },
]

export function DisplayCard() {
  const { hideHoldingValues, setHideHoldingValues, theme, setTheme } = useUI()
  const { profile, refreshProfile } = useAuth()
  const [savingPrivacy, setSavingPrivacy] = useState(false)

  // Réglage du compte (pas du navigateur) : il s'applique sur tous les appareils
  const setPrivacyOnStart = async (enabled: boolean) => {
    setSavingPrivacy(true)
    try {
      await api.put("/admin/profile", { privacy_on_start: enabled })
      await refreshProfile()
      toast.success(enabled ? "L'application s'ouvrira montants masqués" : "Les montants s'afficheront à l'ouverture")
    } catch (error) {
      toast.error(errorMessage(error, "Impossible d'enregistrer le réglage"))
    } finally {
      setSavingPrivacy(false)
    }
  }

  return (
    <Card className="shadow-sm border-slate-100 overflow-hidden">
      <CardHeader className="bg-slate-50/50 border-b">
        <div className="flex items-center gap-2">
          <Layers className="h-5 w-5 text-slate-500" />
          <CardTitle className="text-lg">Affichage</CardTitle>
        </div>
        <CardDescription>Le thème et les positions simplifiées sont propres à cet appareil ; le masquage au démarrage vaut pour tous.</CardDescription>
      </CardHeader>
      <CardContent className="divide-y divide-slate-100 p-4 sm:p-6 [&>*]:py-4 [&>*:first-child]:pt-0 [&>*:last-child]:pb-0">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between sm:gap-4">
          <div className="min-w-0">
            <p className="font-bold text-slate-900">Thème</p>
            <p className="text-sm text-slate-500">« Auto » suit le réglage clair / sombre du système.</p>
          </div>
          <div role="radiogroup" aria-label="Thème" className="grid shrink-0 grid-cols-3 gap-1 rounded-xl bg-slate-100 p-1">
            {THEMES.map(({ value, label, icon: Icon }) => (
              <button
                key={value}
                type="button"
                role="radio"
                aria-checked={theme === value}
                onClick={() => setTheme(value)}
                className={cn(
                  "flex h-10 items-center justify-center gap-1.5 rounded-lg px-3 text-sm font-medium transition-colors sm:h-8",
                  theme === value ? "bg-white text-slate-900 shadow-sm" : "text-slate-500 hover:text-slate-900",
                )}
              >
                <Icon className="h-4 w-4" />
                {label}
              </button>
            ))}
          </div>
        </div>

        <div className="flex items-center justify-between gap-4">
          <div className="min-w-0">
            <Label htmlFor="privacy-on-start" className="font-bold text-slate-900 cursor-pointer">
              Ouvrir avec les montants masqués
            </Label>
            <p className="text-sm text-slate-500">
              Le mode confidentialité (l'œil) est activé à chaque ouverture de l'application, sur tous tes appareils. Tu peux toujours afficher les montants ensuite.
            </p>
          </div>
          <Switch
            id="privacy-on-start"
            checked={profile?.privacy_on_start ?? false}
            disabled={!profile || savingPrivacy}
            onCheckedChange={setPrivacyOnStart}
          />
        </div>

        <div className="flex items-center justify-between gap-4">
          <div className="min-w-0">
            <Label htmlFor="hide-holding-values" className="font-bold text-slate-900 cursor-pointer">
              Positions simplifiées (comptes titres)
            </Label>
            <p className="text-sm text-slate-500">
              N'affiche que le titre (logo, nom, ticker) et le nombre de parts : PRU, cours, valeurs, plus-values, dividendes et poids sont masqués.
            </p>
          </div>
          <Switch
            id="hide-holding-values"
            checked={hideHoldingValues}
            onCheckedChange={setHideHoldingValues}
          />
        </div>
      </CardContent>
    </Card>
  )
}
