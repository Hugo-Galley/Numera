import { toast } from "sonner"
import { useEffect, useState } from "react"
import { AnnualReport, KIND_LABELS, TaxOverview, TaxSettings, WrapperSuggestion } from "./types"
import { patchAccountsById } from "@/lib/api/accounts"
import { getTaxAnnualReport, getTaxOverview, patchTaxSettings } from "@/lib/api/investments"

/** Chargement des enveloppes et du récapitulatif annuel, réglages fiscaux et suggestions. */
export function useTaxData() {
  const currentYear = new Date().getFullYear()
  const [overview, setOverview] = useState<TaxOverview | null>(null)
  const [report, setReport] = useState<AnnualReport | null>(null)
  const [year, setYear] = useState(currentYear)
  const [loadingOverview, setLoadingOverview] = useState(true)
  const [loadingReport, setLoadingReport] = useState(true)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [draft, setDraft] = useState<TaxSettings | null>(null)

  const loadOverview = async () => {
    try {
      const data = await getTaxOverview<TaxOverview>()
      setOverview(data)
      setDraft(data.settings)
    } catch {
      toast.error("Impossible de charger les enveloppes fiscales")
    } finally {
      setLoadingOverview(false)
    }
  }

  useEffect(() => {
    loadOverview()
  }, [])

  useEffect(() => {
    let cancelled = false
    setLoadingReport(true)
    getTaxAnnualReport<AnnualReport>(`?year=${year}`)
      .then((data) => !cancelled && setReport(data))
      .catch(() => !cancelled && toast.error("Impossible de charger le récapitulatif annuel"))
      .finally(() => !cancelled && setLoadingReport(false))
    return () => {
      cancelled = true
    }
  }, [year])

  const saveSettings = async () => {
    if (!draft) return
    try {
      await patchTaxSettings(draft)
      toast.success("Réglages enregistrés")
      await loadOverview()
    } catch {
      toast.error("Erreur lors de l'enregistrement des réglages")
    }
  }

  const applySuggestion = async (s: WrapperSuggestion) => {
    try {
      await patchAccountsById(s.account_id, { tax_wrapper: s.kind })
      toast.success(`${s.account_name} suivi comme ${KIND_LABELS[s.kind]}`)
      await loadOverview()
    } catch {
      toast.error("Impossible d'enregistrer l'enveloppe")
    }
  }

  const cards = (overview?.wrappers ?? []).filter((w) => w.kind !== "cto")
  const suggestions = overview?.suggestions ?? []
  const advice = overview?.allocation_advice ?? []
  const years = Array.from({ length: 6 }, (_, i) => currentYear - i)

  return { currentYear, overview, setOverview, report, setReport, year, setYear, loadingOverview, setLoadingOverview, loadingReport, setLoadingReport, settingsOpen, setSettingsOpen, draft, setDraft, loadOverview, saveSettings, applySuggestion, cards, suggestions, advice, years }
}
