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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { toast } from "sonner"
import { PlusCircle, Layers, Globe } from "lucide-react"

interface CustomEtfModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  initialTicker?: string
  initialName?: string
  initialIsin?: string
  onProfileCreated?: (profile: any) => void
}

const TEMPLATES: Record<string, { countries: Record<string, number>; sectors: Record<string, number>; top_holdings: any[] }> = {
  world: {
    countries: { "USA": 71.0, "JPN": 5.5, "GBR": 3.7, "FRA": 2.8, "DEU": 2.2, "Autres": 14.8 },
    sectors: { "Technologie": 25.0, "Finance": 15.0, "Santé": 12.0, "Industrie": 10.0, "Consommation": 10.0, "Autres": 28.0 },
    top_holdings: [
      { name: "Apple", ticker: "AAPL", weight: 4.8 },
      { name: "Microsoft", ticker: "MSFT", weight: 4.3 },
      { name: "Nvidia", ticker: "NVDA", weight: 4.1 },
      { name: "Amazon", ticker: "AMZN", weight: 2.6 },
      { name: "Alphabet", ticker: "GOOGL", weight: 2.5 },
    ],
  },
  sp500: {
    countries: { "USA": 100.0 },
    sectors: { "Technologie": 31.0, "Finance": 14.0, "Santé": 11.5, "Consommation": 10.0, "Industrie": 8.5, "Autres": 25.0 },
    top_holdings: [
      { name: "Apple", ticker: "AAPL", weight: 7.1 },
      { name: "Microsoft", ticker: "MSFT", weight: 6.5 },
      { name: "Nvidia", ticker: "NVDA", weight: 6.1 },
      { name: "Amazon", ticker: "AMZN", weight: 3.8 },
      { name: "Alphabet", ticker: "GOOGL", weight: 4.3 },
    ],
  },
  europe: {
    countries: { "GBR": 22.0, "FRA": 18.0, "CHE": 14.0, "DEU": 13.5, "NLD": 7.0, "Autres": 25.5 },
    sectors: { "Finance": 18.0, "Santé": 15.0, "Industrie": 15.0, "Consommation": 10.0, "Technologie": 8.0, "Autres": 34.0 },
    top_holdings: [
      { name: "Novo Nordisk", ticker: "NOVO-B.CO", weight: 3.5 },
      { name: "ASML", ticker: "ASML.AS", weight: 3.1 },
      { name: "Nestlé", ticker: "NESN.SW", weight: 2.7 },
      { name: "LVMH", ticker: "MC.PA", weight: 1.8 },
      { name: "TotalEnergies", ticker: "TTE.PA", weight: 1.4 },
    ],
  },
  emerging: {
    countries: { "CHN": 25.0, "IND": 20.0, "TWN": 19.0, "KOR": 11.0, "BRA": 5.0, "Autres": 20.0 },
    sectors: { "Technologie": 24.0, "Finance": 23.0, "Consommation": 13.0, "Industrie": 6.0, "Autres": 34.0 },
    top_holdings: [
      { name: "TSMC", ticker: "TSM", weight: 9.8 },
      { name: "Tencent", ticker: "0700.HK", weight: 4.3 },
      { name: "Samsung", ticker: "005930.KS", weight: 3.9 },
      { name: "Alibaba", ticker: "BABA", weight: 2.4 },
    ],
  },
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
  const [template, setTemplate] = useState("world")
  const [saving, setSaving] = useState(false)
  const [analyzing, setAnalyzing] = useState(false)

  const handleTemplateChange = (val: string) => {
    setTemplate(val)
  }

  const handleAutoDecompose = async () => {
    const symbolToAnalyze = ticker.trim() || isin.trim()
    if (!symbolToAnalyze) {
      toast.error("Veuillez renseigner un symbole ou un code ISIN à décomposer")
      return
    }

    setAnalyzing(true)
    const toastId = toast.loading(`Décomposition en ligne de ${symbolToAnalyze}...`)
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

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim() || !ticker.trim()) {
      toast.error("Veuillez renseigner le nom et le symbole de l'ETF")
      return
    }

    setSaving(true)
    try {
      const tData = TEMPLATES[template] || TEMPLATES.world
      const payload = {
        name: name.trim(),
        ticker: ticker.trim().toUpperCase(),
        isin: isin.trim() ? isin.trim().toUpperCase() : null,
        aliases: [ticker.trim().toUpperCase(), ...(isin.trim() ? [isin.trim().toUpperCase()] : [])],
        countries: tData.countries,
        sectors: tData.sectors,
        top_holdings: tData.top_holdings,
      }

      const created = await api.post("/etf-profiles", payload)
      toast.success("Profil ETF créé avec succès")
      onProfileCreated?.(created)
      onOpenChange(false)
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || "Erreur lors de la création du profil ETF")
    } finally {
      setSaving(false)
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
              Enregistrez la composition sous-jacente de cet ETF pour l'intégrer au scanner de diversité et au calcul de transparence.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4 text-xs">
            <div className="space-y-1">
              <Label htmlFor="etf-ticker" className="text-xs">Ticker / Symbole</Label>
              <div className="flex items-center gap-2">
                <Input
                  id="etf-ticker"
                  placeholder="Ex: 0P0001HI7F.F ou CW8.PA"
                  value={ticker}
                  onChange={(e) => setTicker(e.target.value)}
                  className="h-8 text-xs font-mono uppercase"
                  required
                />
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={handleAutoDecompose}
                  disabled={analyzing || !ticker.trim()}
                  className="h-8 text-xs gap-1.5 shrink-0"
                >
                  <Globe className="h-3.5 w-3.5" />
                  Décomposer en ligne
                </Button>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <Label htmlFor="etf-name" className="text-xs">Nom de l'ETF</Label>
                <Input
                  id="etf-name"
                  placeholder="Ex: Amundi Prime Global"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="h-8 text-xs"
                  required
                />
              </div>
              <div className="space-y-1">
                <Label htmlFor="etf-isin" className="text-xs">Code ISIN (Optionnel)</Label>
                <Input
                  id="etf-isin"
                  placeholder="Ex: FR0014001FD5"
                  value={isin}
                  onChange={(e) => setIsin(e.target.value)}
                  className="h-8 text-xs font-mono uppercase"
                />
              </div>
            </div>

            <div className="space-y-1">
              <Label className="text-xs">Modèle de répartition de base</Label>
              <Select value={template} onValueChange={handleTemplateChange}>
                <SelectTrigger className="h-8 text-xs">
                  <SelectValue placeholder="Choisir un modèle..." />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="world" className="text-xs">Modèle Monde (~71% USA, ~15% Europe, ~5% Japon)</SelectItem>
                  <SelectItem value="sp500" className="text-xs">Modèle USA / S&P 500 (100% USA, 31% Tech)</SelectItem>
                  <SelectItem value="europe" className="text-xs">Modèle Europe / STOXX (UK, France, Suisse, Allemagne)</SelectItem>
                  <SelectItem value="emerging" className="text-xs">Modèle Émergents (Chine, Inde, Taïwan, Corée)</SelectItem>
                </SelectContent>
              </Select>
              <p className="text-[11px] text-muted-foreground mt-1">
                Pré-remplit les 10 premières entreprises et la ventilation géographique/sectorielle de référence.
              </p>
            </div>
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" size="sm" onClick={() => onOpenChange(false)} disabled={saving}>
              Annuler
            </Button>
            <Button
              type="submit"
              size="sm"
              disabled={saving}
              className="gap-2 bg-slate-900 hover:bg-slate-800 text-white shadow-sm"
            >
              <PlusCircle className="h-3.5 w-3.5" />
              {saving ? "Enregistrement..." : "Enregistrer l'ETF"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
