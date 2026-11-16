import { RotateCcw } from "lucide-react"
import { useTranslation } from "react-i18next"
import { toast } from "sonner"
import { Switch } from "@/components/ui/switch"
import { patchRecurringTransactionsById } from "@/lib/api/recurring"

interface EssentialSub {
  name: string
  recurring_id?: number | null
  is_essential?: boolean
  is_essential_source?: "auto" | "manual"
}

/** Case « Essentiel » d'une récurrence : valeur déduite de la catégorie (auto) tant que l'utilisateur ne tranche pas. */
export function EssentialToggle({ sub, onChanged }: { sub: EssentialSub; onChanged: () => void }) {
  const { t } = useTranslation("recurring")
  if (sub.recurring_id == null) return null
  const id = sub.recurring_id
  const isAuto = sub.is_essential_source !== "manual"
  const save = async (value: boolean | null) => {
    try {
      await patchRecurringTransactionsById(id, { is_essential: value })
      onChanged()
    } catch {
      toast.error(t("essentials.saveError"))
    }
  }
  return (
    // La ligne entière ouvre le détail du flux : la case ne doit pas le déclencher
    <div className="flex items-center gap-1.5" onClick={(e) => e.stopPropagation()}>
      <Switch
        checked={!!sub.is_essential}
        onCheckedChange={(checked) => save(checked)}
        aria-label={t("essentials.toggleLabel", { name: sub.name })}
        className="h-5 w-9 [&>span]:h-4 [&>span]:w-4 [&>span[data-state=checked]]:translate-x-4"
      />
      <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">
        {t("essentials.essential")}
        {isAuto && <span className="ml-1 font-medium normal-case tracking-normal text-slate-400">{t("essentials.auto")}</span>}
      </span>
      {!isAuto && (
        <button
          type="button"
          onClick={() => save(null)}
          title={t("essentials.resetAuto")}
          aria-label={t("essentials.resetAuto")}
          className="rounded p-0.5 text-slate-400 hover:text-slate-700"
        >
          <RotateCcw className="h-3 w-3" />
        </button>
      )}
    </div>
  )
}
