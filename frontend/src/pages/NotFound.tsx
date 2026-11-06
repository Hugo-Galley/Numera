import { Link } from "react-router-dom"
import { useTranslation } from "react-i18next"
import { Compass } from "lucide-react"
import { Button } from "@/components/ui/button"

export default function NotFound() {
  const { t } = useTranslation()
  return (
    <div className="flex h-[60vh] flex-col items-center justify-center gap-4 text-center">
      <Compass className="h-12 w-12 text-slate-300" />
      <div>
        <h1 className="text-2xl font-bold text-slate-900">{t("notFound.title")}</h1>
        <p className="mt-1 text-sm text-slate-500">{t("notFound.text")}</p>
      </div>
      <Button asChild>
        <Link to="/">{t("notFound.back")}</Link>
      </Button>
    </div>
  )
}
