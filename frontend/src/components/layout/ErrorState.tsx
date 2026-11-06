import { AlertTriangle } from "lucide-react"
import { useTranslation } from "react-i18next"
import { Button } from "@/components/ui/button"

interface ErrorStateProps {
  message?: string
  onRetry?: () => void
  className?: string
}

/** État d'erreur commun : distingue « pas de données » d'un chargement qui a échoué. */
export function ErrorState({ message, onRetry, className = "" }: ErrorStateProps) {
  const { t } = useTranslation()
  return (
    <div role="alert" className={`flex flex-col items-center justify-center gap-3 rounded-xl border border-amber-200 bg-amber-50 p-6 text-center ${className}`}>
      <AlertTriangle className="h-6 w-6 text-amber-600" />
      <p className="text-sm font-medium text-amber-900">{message ?? t("errors.loadFailed")}</p>
      {onRetry && (
        <Button variant="outline" size="sm" onClick={onRetry}>
          {t("errors.retry")}
        </Button>
      )}
    </div>
  )
}
