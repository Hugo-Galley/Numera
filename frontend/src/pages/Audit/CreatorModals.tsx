import i18n from "i18next"
import { useTranslation } from "react-i18next"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { RefreshCw, Save } from "lucide-react"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { toast } from "sonner"
import { useState } from "react"
import { Category } from "./types"
import { postCategorizationRules, postMerchants, postMerchantsAutoNormalize } from "@/lib/api/classement"

export function RuleCreatorModal({
  merchant,
  suggestedCategoryId,
  categories,
  onCreated,
  onClose,
}: {
  merchant: string
  suggestedCategoryId?: number
  categories: Category[]
  onCreated: () => void
  onClose: () => void
}) {
  const { t } = useTranslation("audit")
  const [draft, setDraft] = useState({
    pattern: merchant,
    category_id: suggestedCategoryId ? String(suggestedCategoryId) : "none",
  })
  const [saving, setSaving] = useState(false)

  async function create() {
    setSaving(true)
    try {
      await postCategorizationRules({
        pattern: draft.pattern.trim(),
        category_id: draft.category_id === "none" ? null : Number(draft.category_id),
        priority: 0,
      })
      toast.success(t("creatorModals.regleCreee"))
      onCreated()
      onClose()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : t("creatorModals.creationImpossible"))
    } finally {
      setSaving(false)
    }
  }

  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent className="[&_input]:text-base md:[&_input]:text-sm">
        <DialogHeader>
          <DialogTitle>{t("creatorModals.creerUneRegleDAuto")}</DialogTitle>
          <DialogDescription>
            {i18n.t("misc.ruleHint", { ns: "audit", merchant })}
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <p className="text-sm font-medium">{t("creatorModals.motClePattern")}</p>
            <Input value={draft.pattern} onChange={(e) => setDraft({...draft, pattern: e.target.value})} />
          </div>
          <div className="space-y-2">
            <p className="text-sm font-medium">{t("creatorModals.categorieCible")}</p>
            <Select value={draft.category_id} onValueChange={(v) => setDraft({...draft, category_id: v})}>
              <SelectTrigger>
                <SelectValue placeholder={t("creatorModals.choisirUneCategorie")} />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="none">{t("creatorModals.aucune")}</SelectItem>
                {categories.map((c) => (
                  <SelectItem key={c.id} value={String(c.id)}>{c.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
        <DialogFooter className="gap-2 sm:gap-0">
          <Button variant="outline" className="h-11 sm:h-10" onClick={onClose}>{t("creatorModals.annuler")}</Button>
          <Button className="h-11 sm:h-10" onClick={create} disabled={saving}>
            {saving ? <RefreshCw className="h-4 w-4 animate-spin mr-2" /> : <Save className="h-4 w-4 mr-2" />}
            {t("creatorModals.creerLaRegle")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

export function MerchantCreatorModal({
  merchant,
  variants,
  categories,
  onCreated,
  onClose,
}: {
  merchant: string
  variants?: string[]
  categories: Category[]
  onCreated: () => void
  onClose: () => void
}) {
  const { t } = useTranslation("audit")
  const [draft, setDraft] = useState({
    name: merchant,
    category_id: "none",
  })
  const [saving, setSaving] = useState(false)

  async function create() {
    setSaving(true)
    try {
      await postMerchants({
        name: draft.name.trim(),
        category_id: draft.category_id === "none" ? null : Number(draft.category_id),
        // Toutes les écritures repérées par le Centre d'actions, pas seulement la plus fréquente
        aliases: variants?.length ? variants : [merchant]
      })
      toast.success(t("creatorModals.marchandCreeEtNormalise"))
      await postMerchantsAutoNormalize({})
      onCreated()
      onClose()
    } catch (err) {
      toast.error(err instanceof Error ? err.message : t("creatorModals.creationImpossible"))
    } finally {
      setSaving(false)
    }
  }

  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent className="[&_input]:text-base md:[&_input]:text-sm">
        <DialogHeader>
          <DialogTitle>{t("creatorModals.normaliserLeMarchand")}</DialogTitle>
          <DialogDescription>
            {i18n.t("misc.merchantHint", { ns: "audit", merchant })}
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <p className="text-sm font-medium">{t("creatorModals.nomCanonique")}</p>
            <Input value={draft.name} onChange={(e) => setDraft({...draft, name: e.target.value})} />
          </div>
          <div className="space-y-2">
            <p className="text-sm font-medium">{t("creatorModals.categorieParDefaut")}</p>
            <Select value={draft.category_id} onValueChange={(v) => setDraft({...draft, category_id: v})}>
              <SelectTrigger>
                <SelectValue placeholder={t("creatorModals.choisirUneCategorie")} />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="none">{t("creatorModals.aucune")}</SelectItem>
                {categories.map((c) => (
                  <SelectItem key={c.id} value={String(c.id)}>{c.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
        <DialogFooter className="gap-2 sm:gap-0">
          <Button variant="outline" className="h-11 sm:h-10" onClick={onClose}>{t("creatorModals.annuler")}</Button>
          <Button className="h-11 sm:h-10" onClick={create} disabled={saving}>
            {saving ? <RefreshCw className="h-4 w-4 animate-spin mr-2" /> : <Save className="h-4 w-4 mr-2" />}
            {t("creatorModals.creerEtNormaliser")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
