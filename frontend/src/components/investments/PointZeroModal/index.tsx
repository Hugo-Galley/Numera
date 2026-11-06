import i18n from "i18next"
import { useTranslation } from "react-i18next"
import { CustomEtfModal } from "../CustomEtfModal"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { SlidersHorizontal } from "lucide-react"
import { PointZeroModalProps } from "./types"
import { usePointZeroModal } from "./usePointZeroModal"
import { PointZeroSearch } from "./PointZeroSearch"
import { PointZeroRows } from "./PointZeroRows"
import { PointZeroFooter } from "./PointZeroFooter"

export function PointZeroModal({
  open,
  onOpenChange,
  accountId,
  accountName,
  onBaselineSaved,
}: PointZeroModalProps) {
  const { t } = useTranslation("investments")
  const ctx = usePointZeroModal(open, onOpenChange, accountId, accountName, onBaselineSaved)
  const { customEtfOpen, handleSelectSearchResult, pendingEtfSearch, setCustomEtfOpen } = ctx
  return (
    <>
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="max-w-3xl max-h-[calc(100dvh-2*max(1rem,env(safe-area-inset-top)))] flex flex-col p-4 sm:p-6">
          <DialogHeader>
            <div className="flex items-center gap-2">
              <SlidersHorizontal className="h-5 w-5 shrink-0 text-slate-800" />
              <DialogTitle className="pr-6 text-left text-lg font-bold text-slate-900">{i18n.t("misc.zeroPointTitle", { ns: "investments", name: accountName })}</DialogTitle>
            </div>
            <DialogDescription className="hidden text-xs text-slate-500 sm:block">
              {t("index.declarezVosPositionsActuellesLes")}
            </DialogDescription>
          </DialogHeader>

          <PointZeroSearch ctx={ctx} />

          <PointZeroRows ctx={ctx} />

          <PointZeroFooter ctx={ctx} />
        </DialogContent>
      </Dialog>

      {/* Modal for creating custom ETF */}
      <CustomEtfModal
        open={customEtfOpen}
        onOpenChange={setCustomEtfOpen}
        initialTicker={pendingEtfSearch}
        initialName={pendingEtfSearch}
        onProfileCreated={(profile) => {
          handleSelectSearchResult({
            symbol: profile.ticker,
            name: profile.name,
            isin: profile.isin,
            type: "ETF",
            currency: "EUR",
            etf_profile_id: profile.id,
          })
        }}
      />
    </>
  )
}
