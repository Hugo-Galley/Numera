import { useMerchantsTab } from "./useMerchantsTab"
import { MerchantsActions } from "./MerchantsActions"
import { MerchantsList } from "./MerchantsList"
import { SuggestionsPanel } from "./SuggestionsPanel"
import { EditMerchantDialog } from "./EditMerchantDialog"

export function MerchantsTab() {
  const ctx = useMerchantsTab()
  return (
    <div className="space-y-6 md:space-y-8 [&_input]:text-base md:[&_input]:text-sm">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl md:text-2xl font-bold text-slate-900">Normalisation des marchands</h2>
          <p className="text-slate-500 text-sm mt-1">Regroupez les variantes de libellés bancaires sous un marchand unique.</p>
        </div>
        
        <MerchantsActions ctx={ctx} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 lg:gap-8">
          <MerchantsList ctx={ctx} />

        <SuggestionsPanel ctx={ctx} />
      </div>

      {/* Edit Dialog */}
      <EditMerchantDialog ctx={ctx} />
    </div>
  )
}
