import { useState } from "react"
import { useTranslation } from "react-i18next"
import { toast } from "sonner"
import { Check, Pencil, X } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { useSubmit } from "@/hooks/useSubmit"
import { putHoldingsById } from "@/lib/api/investments"
import { errorMessage } from "@/lib/utils"
import type { PortfolioHolding } from "@/types/diversity"

const ISIN_FORMAT = /^[A-Z]{2}[A-Z0-9]{9}\d$/

/** « ISIN à compléter » : un clic ouvre la saisie sur place, comme pour le PRU. */
export function MissingIsin({ holding, onSaved }: { holding: PortfolioHolding; onSaved: () => void }) {
  const { t } = useTranslation("investments")
  const [draft, setDraft] = useState<string | null>(null)

  const [save, saving] = useSubmit(async () => {
    const isin = (draft ?? "").trim().toUpperCase()
    if (!ISIN_FORMAT.test(isin)) {
      toast.error(t("missingIsin.invalid"))
      return
    }
    try {
      await putHoldingsById(holding.id, { isin })
      toast.success(t("missingIsin.saved", { ticker: holding.ticker }))
      setDraft(null)
      onSaved()
    } catch (err) {
      toast.error(errorMessage(err, t("missingIsin.saveError")))
    }
  })

  if (draft === null) {
    return (
      <button type="button" onClick={() => setDraft("")} className="inline-flex min-h-10 items-center gap-1 font-sans text-[11px] italic text-amber-700 md:min-h-0">
        {t("missingIsin.action")}
        <Pencil className="h-3 w-3" aria-hidden="true" />
      </button>
    )
  }
  return (
    <span className="flex items-center gap-1">
      <Input
        autoFocus
        value={draft}
        maxLength={14}
        placeholder="ISIN"
        onChange={(e) => setDraft(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter") save()
          if (e.key === "Escape") setDraft(null)
        }}
        className="h-10 w-40 font-mono text-base uppercase md:h-7 md:text-xs"
        aria-label={t("missingIsin.field", { ticker: holding.ticker })}
      />
      <Button variant="ghost" size="icon" className="h-10 w-10 shrink-0 text-emerald-600 md:h-7 md:w-7" onClick={() => save()} disabled={saving} aria-label={t("missingIsin.save")}>
        <Check className="h-4 w-4" />
      </Button>
      <Button variant="ghost" size="icon" className="h-10 w-10 shrink-0 text-slate-400 md:h-7 md:w-7" onClick={() => setDraft(null)} aria-label={t("missingIsin.cancel")}>
        <X className="h-4 w-4" />
      </Button>
    </span>
  )
}
