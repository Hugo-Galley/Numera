import { useState } from "react"
import { api } from "@/lib/api"
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
  const [name, setName] = useState(initialName)
  const [ticker, setTicker] = useState(initialTicker)
  const [isin, setIsin] = useState(initialIsin)
  const [analyzing, setAnalyzing] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const symbolToAnalyze = ticker.trim() || isin.trim()
    if (!symbolToAnalyze) {
      toast.error("Veuillez renseigner le symbole Yahoo du fonds")
      return
    }

    setAnalyzing(true)
    const toastId = toast.loading(`Récupération de la composition de ${symbolToAnalyze} sur Yahoo...`)
    try {
      const result = await api.post<any>("/etf-profiles/auto-decompose", {
        symbol: symbolToAnalyze,
        name: name.trim() || undefined,
        isin: isin.trim() || undefined,
      })
      if (result && result.id) {
        setName(result.name)
        setTicker(result.ticker)
        if (result.isin) setIsin(result.isin)
        toast.success(`${result.name} décomposé avec succès !`, { id: toastId })
        onProfileCreated?.(result)
        onOpenChange(false)
      } else {
        toast.error("Impossible de décomposer ce fonds en ligne", { id: toastId })
      }
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || "Erreur lors de la décomposition en ligne", { id: toastId })
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
              <DialogTitle className="text-base font-bold">Définir un profil d'ETF</DialogTitle>
            </div>
            <DialogDescription className="text-xs">
              La composition (secteurs et top 10) est récupérée sur Yahoo Finance puis actualisée chaque semaine. Yahoo ne publie pas la répartition par pays.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4 text-xs">
            <div className="space-y-1">
              <Label htmlFor="etf-ticker" className="text-xs">Ticker / Symbole</Label>
              <Input
                id="etf-ticker"
                placeholder="Ex: 0P0001HI7F.F ou CW8.PA"
                value={ticker}
                onChange={(e) => setTicker(e.target.value)}
                className="h-11 text-base font-mono uppercase sm:h-8 sm:text-xs"
                required
              />
            </div>

            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div className="space-y-1">
                <Label htmlFor="etf-name" className="text-xs">Nom (optionnel)</Label>
                <Input
                  id="etf-name"
                  placeholder="Ex: Amundi Prime Global"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="h-11 text-base sm:h-8 sm:text-xs"
                />
              </div>
              <div className="space-y-1">
                <Label htmlFor="etf-isin" className="text-xs">Code ISIN (Optionnel)</Label>
                <Input
                  id="etf-isin"
                  placeholder="Ex: FR0014001FD5"
                  value={isin}
                  onChange={(e) => setIsin(e.target.value)}
                  className="h-11 text-base font-mono uppercase sm:h-8 sm:text-xs"
                />
              </div>
            </div>
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" size="sm" className="h-11 sm:h-8" onClick={() => onOpenChange(false)} disabled={analyzing}>
              Annuler
            </Button>
            <Button
              type="submit"
              size="sm"
              disabled={analyzing || !ticker.trim()}
              className="h-11 gap-2 bg-slate-900 text-white shadow-sm hover:bg-slate-800 sm:h-8"
            >
              <Globe className="h-3.5 w-3.5" />
              {analyzing ? "Récupération..." : "Créer depuis Yahoo"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
