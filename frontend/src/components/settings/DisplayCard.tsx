import { useState } from "react"
import { Layers, Monitor, Moon, Sun } from "lucide-react"
import { toast } from "sonner"
import { useTranslation } from "react-i18next"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Switch } from "@/components/ui/switch"
import { api } from "@/lib/api"
import { type Language, LANGUAGES, setLanguage } from "@/i18n"
import { syncServerLanguage } from "@/lib/serverLanguage"
import { cn, errorMessage } from "@/lib/utils"
import { useAuth } from "@/providers/AuthProvider"
import { type ThemePreference, useUI } from "@/providers/UIProvider"

const THEMES = [
  { value: "light", label: "light", icon: Sun },
  { value: "dark", label: "dark", icon: Moon },
  { value: "system", label: "auto", icon: Monitor },
] as const satisfies readonly { value: ThemePreference; label: string; icon: typeof Sun }[]

// Chaque langue s'écrit dans sa propre langue, pour rester repérable quand l'interface est illisible pour l'utilisateur
const LANGUAGE_NAMES: Record<Language, string> = { fr: "Français", en: "English", es: "Español" }
const LANGUAGE_FLAGS: Record<Language, string> = { fr: "🇫🇷", en: "🇬🇧", es: "🇪🇸" }

export function DisplayCard() {
  const { t, i18n } = useTranslation("settings")
  const { hideHoldingValues, setHideHoldingValues, theme, setTheme } = useUI()
  const { profile, refreshProfile } = useAuth()
  const [savingPrivacy, setSavingPrivacy] = useState(false)

  // Réglage du compte (pas du navigateur) : il s'applique sur tous les appareils
  const setPrivacyOnStart = async (enabled: boolean) => {
    setSavingPrivacy(true)
    try {
      await api.put("/admin/profile", { privacy_on_start: enabled })
      await refreshProfile()
      toast.success(enabled ? t("display.privacyOnStart.enabled") : t("display.privacyOnStart.disabled"))
    } catch (error) {
      toast.error(errorMessage(error, t("display.privacyOnStart.error")))
    } finally {
      setSavingPrivacy(false)
    }
  }

  return (
    <Card className="shadow-sm border-slate-100 overflow-hidden">
      <CardHeader className="bg-slate-50/50 border-b">
        <div className="flex items-center gap-2">
          <Layers className="h-5 w-5 text-slate-500" />
          <CardTitle className="text-lg">{t("display.title")}</CardTitle>
        </div>
        <CardDescription>{t("display.description")}</CardDescription>
      </CardHeader>
      <CardContent className="divide-y divide-slate-100 p-4 sm:p-6 [&>*]:py-4 [&>*:first-child]:pt-0 [&>*:last-child]:pb-0">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between sm:gap-4">
          <div className="min-w-0">
            <p className="font-bold text-slate-900">{t("display.language.title")}</p>
            <p className="text-sm text-slate-500">{t("display.language.hint")}</p>
          </div>
          <Select
            value={i18n.language}
            onValueChange={(code) => { void setLanguage(code as Language); void syncServerLanguage(code as Language) }}
          >
            <SelectTrigger aria-label={t("display.language.aria")} className="w-full shrink-0 sm:w-44">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {LANGUAGES.map((code) => (
                <SelectItem key={code} value={code} lang={code}>
                  <span className="flex items-center gap-2">
                    <span aria-hidden="true">{LANGUAGE_FLAGS[code]}</span>
                    {LANGUAGE_NAMES[code]}
                  </span>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between sm:gap-4">
          <div className="min-w-0">
            <p className="font-bold text-slate-900">{t("display.theme.title")}</p>
            <p className="text-sm text-slate-500">{t("display.theme.hint")}</p>
          </div>
          <div role="radiogroup" aria-label={t("display.theme.title")} className="grid shrink-0 grid-cols-3 gap-1 rounded-xl bg-slate-100 p-1">
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
                {t(`display.theme.${label}`)}
              </button>
            ))}
          </div>
        </div>

        <div className="flex items-center justify-between gap-4">
          <div className="min-w-0">
            <Label htmlFor="privacy-on-start" className="font-bold text-slate-900 cursor-pointer">
              {t("display.privacyOnStart.label")}
            </Label>
            <p className="text-sm text-slate-500">
              {t("display.privacyOnStart.hint")}
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
              {t("display.simplifiedHoldings.label")}
            </Label>
            <p className="text-sm text-slate-500">
              {t("display.simplifiedHoldings.hint")}
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
