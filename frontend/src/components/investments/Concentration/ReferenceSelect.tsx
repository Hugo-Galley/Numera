import { useState } from "react"
import { useTranslation } from "react-i18next"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { putAnalyticsDiversityScannerMarketReference } from "@/lib/api/analytics"

const DEFAULT = "__default__"

export interface ReferenceCandidate {
  ticker: string
  name: string
}

/** Choix du profil de marché qui sert de référence (vide = MSCI ACWI par défaut). */
export function ReferenceSelect({ current, candidates, onChange }: {
  /** Ticker de la référence en cours, null pour le défaut */
  current: string | null
  /** Profils proposés, la référence en cours comprise */
  candidates: ReferenceCandidate[]
  onChange: () => void
}) {
  const { t } = useTranslation("investments")
  const [custom, setCustom] = useState("")
  const [saving, setSaving] = useState(false)

  const choose = async (ticker: string | null) => {
    setSaving(true)
    try {
      await putAnalyticsDiversityScannerMarketReference({ ticker })
      setCustom("")
      toast.success(t("concentration.reference.saved"))
      onChange()
    } catch {
      toast.error(t("concentration.reference.error"))
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="flex flex-wrap items-center gap-2">
      <Select value={current ?? DEFAULT} onValueChange={(value) => void choose(value === DEFAULT ? null : value)} disabled={saving}>
        <SelectTrigger className="w-full sm:w-56" aria-label={t("concentration.reference.label")}><SelectValue /></SelectTrigger>
        <SelectContent>
          <SelectItem value={DEFAULT}>{t("concentration.reference.default")}</SelectItem>
          {candidates.map((c) => <SelectItem key={c.ticker} value={c.ticker}>{c.name} ({c.ticker})</SelectItem>)}
        </SelectContent>
      </Select>
      <form className="flex gap-2" onSubmit={(e) => { e.preventDefault(); if (custom.trim()) void choose(custom.trim()) }}>
        <Input value={custom} onChange={(e) => setCustom(e.target.value)} placeholder={t("concentration.reference.other")} className="w-32" aria-label={t("concentration.reference.other")} />
        <Button type="submit" variant="outline" disabled={saving || !custom.trim()}>{t("concentration.reference.apply")}</Button>
      </form>
    </div>
  )
}
