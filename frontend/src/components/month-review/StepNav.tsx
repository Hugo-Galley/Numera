/** Barre sous chaque étape de la revue : « Précédent », reste à traiter, puis l'action qui mène à l'étape suivante. */
import { useTranslation } from "react-i18next"
import { ArrowLeft, ArrowRight, Lock } from "lucide-react"

import { Button } from "@/components/ui/button"

interface Props {
  /** Étape courante, à partir de 0. */
  step: number
  /** Nom de l'étape suivante ; `null` sur la dernière. */
  nextName: string | null
  /** Ce qui reste à traiter dans l'étape (« Il reste 2 comptes à vérifier »), `null` si rien. */
  pending: string | null
  /** Dernière étape : le mois est déjà clôturé, plus de bouton principal. */
  closed: boolean
  busy: boolean
  onPrevious: () => void
  onNext: () => void
  onClose: () => void
}

export function StepNav({ step, nextName, pending, closed, busy, onPrevious, onNext, onClose }: Props) {
  const { t } = useTranslation("month")
  const isLast = nextName === null

  return (
    <nav aria-label={t("monthReview.navigation")} className="space-y-3 border-t border-slate-200 pt-4">
      {pending && <p className="text-sm text-amber-700 sm:text-right">{pending}</p>}
      <div className="flex flex-col-reverse gap-2 sm:flex-row sm:items-center sm:justify-between">
        {step > 0 ? (
          <Button variant="ghost" className="h-11 w-full sm:h-10 sm:w-auto" onClick={onPrevious}>
            <ArrowLeft className="h-4 w-4" /> {t("monthReview.precedent")}
          </Button>
        ) : (
          <span className="hidden sm:block" />
        )}
        {isLast ? (
          !closed && (
            <Button className="h-11 w-full sm:h-10 sm:w-auto" onClick={onClose} disabled={busy}>
              <Lock className="h-4 w-4" /> {t("closeStep.cloturerLeMois")}
            </Button>
          )
        ) : (
          <Button className="h-11 w-full sm:h-10 sm:w-auto" variant={pending ? "outline" : "default"} onClick={onNext}>
            {pending ? t("monthReview.passerQuandMeme") : t("monthReview.suivant", { step: nextName })}
            <ArrowRight className="h-4 w-4" />
          </Button>
        )}
      </div>
    </nav>
  )
}
