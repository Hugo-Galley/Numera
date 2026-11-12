import i18n from "i18next"
import { useTranslation } from "react-i18next"
import { errorMessage } from "@/lib/utils"
import { useEffect, useState } from "react"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { toast } from "sonner"
import { Layers, Globe } from "lucide-react"
import { postEtfProfilesAutoDecompose } from "@/lib/api/investments"

interface CustomEtfModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  initialTicker?: string
  initialName?: string
  initialIsin?: string
  onProfileCreated?: (profile: any) => void
}

export function CustomEtfModal({
  open,
  onOpenChange,
  initialTicker = "",
  initialName = "",
  initialIsin = "",
  onProfileCreated,
}: CustomEtfModalProps) {
  const { t } = useTranslation("investments")
  const [name, setName] = useState(initialName)
  const [ticker, setTicker] = useState(initialTicker)
  const [isin, setIsin] = useState(initialIsin)
  const [analyzing, setAnalyzing] = useState(false)

  // La fenêtre reste montée entre deux ouvertures : à chaque ouverture, le formulaire repart de la recherche en cours
  useEffect(() => {
    if (!open) return
    setName(initialName)
    setTicker(initialTicker)
    setIsin(initialIsin)
  }, [open, initialName, initialTicker, initialIsin])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const symbolToAnalyze = ticker.trim() || isin.trim()
    if (!symbolToAnalyze) {
      toast.error(t("customEtfModal.veuillezRenseignerLeSymboleYahoo"))
      return
    }

    setAnalyzing(true)
    const toastId = toast.loading(i18n.t("misc.fetchingComposition", { ns: "investments", symbol: symbolToAnalyze }))
    try {
      const result = await postEtfProfilesAutoDecompose({
        symbol: symbolToAnalyze,
        name: name.trim() || undefined,
        isin: isin.trim() || undefined,
      })
      if (result && result.id) {
        setName(result.name)
        setTicker(result.ticker)
        if (result.isin) setIsin(result.isin)
        toast.success(i18n.t("misc.brokenDown", { ns: "investments", name: result.name }), { id: toastId })
        onProfileCreated?.(result)
        onOpenChange(false)
      } else {
        toast.error(t("customEtfModal.impossibleDeDecomposerCeFonds"), { id: toastId })
      }
    } catch (err) {
      toast.error(errorMessage(err, t("customEtfModal.erreurLorsDeLaDecomposition")), { id: toastId })
    } finally {
      setAnalyzing(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <form onSubmit={handleSubmit}>
          <DialogHeader>
            <div className="flex items-center gap-2">
              <Layers className="h-5 w-5 text-slate-800" />
              <DialogTitle className="text-base font-bold">{t("customEtfModal.definirUnProfilDEtf")}</DialogTitle>
            </div>
            <DialogDescription className="text-xs">
              {t("customEtfModal.laCompositionSecteursEtTop")}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4 text-xs">
            <div className="space-y-1">
              <Label htmlFor="etf-ticker" className="text-xs">{t("customEtfModal.tickerSymbole")}</Label>
              <Input
                id="etf-ticker"
                placeholder={t("customEtfModal.ex0p0001hi7fFOuCw8")}
                value={ticker}
                onChange={(e) => setTicker(e.target.value)}
                className="h-11 text-base font-mono uppercase sm:h-8 sm:text-xs"
                required
              />
            </div>

            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div className="space-y-1">
                <Label htmlFor="etf-name" className="text-xs">{t("customEtfModal.nomOptionnel")}</Label>
                <Input
                  id="etf-name"
                  placeholder={t("customEtfModal.exAmundiPrimeGlobal")}
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="h-11 text-base sm:h-8 sm:text-xs"
                />
              </div>
              <div className="space-y-1">
                <Label htmlFor="etf-isin" className="text-xs">{t("customEtfModal.codeIsinOptionnel")}</Label>
                <Input
                  id="etf-isin"
                  placeholder={t("customEtfModal.exFr0014001fd5")}
                  value={isin}
                  onChange={(e) => setIsin(e.target.value)}
                  className="h-11 text-base font-mono uppercase sm:h-8 sm:text-xs"
                />
              </div>
            </div>
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" size="sm" className="h-11 sm:h-8" onClick={() => onOpenChange(false)} disabled={analyzing}>
              {t("customEtfModal.annuler")}
            </Button>
            <Button
              type="submit"
              size="sm"
              disabled={analyzing || !ticker.trim()}
              className="h-11 gap-2 bg-slate-900 text-white shadow-sm hover:bg-slate-800 sm:h-8"
            >
              <Globe className="h-3.5 w-3.5" />
              {analyzing ? t("customEtfModal.recuperation") : t("customEtfModal.creerDepuisYahoo")}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
