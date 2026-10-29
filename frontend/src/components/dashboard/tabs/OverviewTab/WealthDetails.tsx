import { AccountLogo } from "@/components/ui/AccountLogo"
import { formatCurrency, formatRate } from "@/lib/utils"
import type { OverviewTabCtx } from "./useOverviewTab"

/** Détail du patrimoine selon le regroupement choisi. */
export function WealthDetails({ ctx }: { ctx: OverviewTabCtx }) {
  const { CATEGORY_COLORS, CATEGORY_LABELS, flatItems, groupBy, groupedItems, institutionData, mixedItems, patrimoineAllocation } = ctx
  return (
    <>
      {/* Grouped, Mixed or Flat Details List */}
      <div className="lg:col-span-7 min-w-0 space-y-4 md:max-h-[300px] md:overflow-y-auto md:pr-2 scrollbar-thin scrollbar-thumb-slate-200">
        {groupBy === "category" ? (
          Object.entries(groupedItems).map(([type, group]: [string, any]) => {
            if (group.items.length === 0) return null;
            const catLabel = CATEGORY_LABELS[type] || type;
            const catColor = CATEGORY_COLORS[type] || "#64748b";
            const totalPatrimoine = patrimoineAllocation.total_patrimoine || 1;
            const catPercentage = ((group.total_eur / totalPatrimoine) * 100).toFixed(1);

            return (
              <div key={type} className="space-y-2">
                {/* Group Header */}
                <div className="flex items-center justify-between border-b border-slate-100 pb-1.5 px-1 bg-slate-50/30">
                  <span className="min-w-0 truncate text-xs font-black tracking-wider text-slate-500 uppercase">
                    {catLabel}
                  </span>
                  <div className="shrink-0 whitespace-nowrap pl-2 text-right">
                    <span className="text-xs font-extrabold text-slate-700 amount-blur">
                      {formatCurrency(group.total_eur, "EUR")}
                    </span>
                    <span className="text-[10px] text-slate-400 font-semibold ml-2">
                      {formatRate(Number(catPercentage), 1)}
                    </span>
                  </div>
                </div>

                {/* Accounts in Group */}
                <div className="space-y-1.5">
                  {group.items.map((item: any) => (
                    <div 
                      key={`${item.account_id}-${item.account_name}`} 
                      className="flex items-center justify-between p-2.5 rounded-xl border border-slate-100 hover:border-slate-200 hover:bg-slate-50/50 transition-all group/item"
                    >
                      <div className="flex min-w-0 items-center gap-2.5">
                        <div 
                          className="h-2 w-2 rounded-full flex-shrink-0" 
                          style={{ backgroundColor: catColor }} 
                        />
                        <AccountLogo accountId={item.account_id} className="h-6 w-6" />
                        <div className="min-w-0">
                          <span className="block truncate font-bold text-slate-800 text-sm group-hover/item:text-slate-900 transition-colors">
                            {item.account_name}
                          </span>
                          {item.currency !== "EUR" && (
                            <span className="text-[10px] text-slate-400 font-medium block">
                              Original: {formatCurrency(item.balance, item.currency)}
                            </span>
                          )}
                        </div>
                      </div>
                      <div className="shrink-0 whitespace-nowrap text-right pl-2">
                        <span className="font-bold text-sm text-slate-900 block amount-blur">
                          {formatCurrency(item.balance_eur, "EUR")}
                        </span>
                        <span className="text-[10px] font-medium text-slate-400">
                          {formatRate((item.balance_eur / totalPatrimoine) * 100, 1)}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            );
          })
        ) : groupBy === "institution" ? (
          institutionData.map((group: any) => {
            const totalPatrimoine = patrimoineAllocation.total_patrimoine || 1;
            return (
              <div key={group.name} className="space-y-2">
                {/* Group Header */}
                <div className="flex items-center justify-between border-b border-slate-100 pb-1.5 px-1 bg-slate-50/30">
                  <span className="min-w-0 truncate text-xs font-black tracking-wider text-slate-500 uppercase">
                    {group.name}
                  </span>
                  <div className="shrink-0 whitespace-nowrap pl-2 text-right">
                    <span className="text-xs font-extrabold text-slate-700 amount-blur">
                      {formatCurrency(group.value, "EUR")}
                    </span>
                    <span className="text-[10px] text-slate-400 font-semibold ml-2">
                      {formatRate(group.percentage, 1)}
                    </span>
                  </div>
                </div>

                {/* Accounts in Group */}
                <div className="space-y-1.5">
                  {group.items.map((item: any) => (
                    <div 
                      key={`${item.account_id}-${item.account_name}`} 
                      className="flex items-center justify-between p-2.5 rounded-xl border border-slate-100 hover:border-slate-200 hover:bg-slate-50/50 transition-all group/item"
                    >
                      <div className="flex min-w-0 items-center gap-2.5">
                        <div 
                          className="h-2 w-2 rounded-full flex-shrink-0" 
                          style={{ backgroundColor: group.color }} 
                        />
                        <AccountLogo accountId={item.account_id} className="h-6 w-6" />
                        <div className="min-w-0">
                          <span className="block truncate font-bold text-slate-800 text-sm group-hover/item:text-slate-900 transition-colors">
                            {item.account_name}
                          </span>
                          {item.currency !== "EUR" && (
                            <span className="text-[10px] text-slate-400 font-medium block">
                              Original: {formatCurrency(item.balance, item.currency)}
                            </span>
                          )}
                        </div>
                      </div>
                      <div className="shrink-0 whitespace-nowrap text-right pl-2">
                        <span className="font-bold text-sm text-slate-900 block amount-blur">
                          {formatCurrency(item.balance_eur, "EUR")}
                        </span>
                        <span className="text-[10px] font-medium text-slate-400">
                          {formatRate((item.balance_eur / totalPatrimoine) * 100, 1)}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            );
          })
        ) : groupBy === "mixed" ? (
          mixedItems.map((item: any) => (
            <div 
              key={item.id} 
              className="flex items-center justify-between p-3 rounded-xl border border-slate-100 hover:border-slate-200 hover:bg-slate-50/50 transition-all group/item"
            >
              <div className="flex min-w-0 items-center gap-3">
                <div 
                  className="h-3 w-3 rounded-full flex-shrink-0" 
                  style={{ backgroundColor: item.color }} 
                />
                <div className="min-w-0">
                  <span className="block truncate font-bold text-slate-800 text-sm group-hover/item:text-slate-900 transition-colors">
                    {item.name}
                  </span>
                  <div className="flex items-center gap-2 mt-0.5">
                    <span className="text-[10px] uppercase font-bold tracking-wider px-1.5 py-0.5 rounded bg-slate-100 text-slate-500">
                      {item.type === "courant" ? "Courant" : item.type === "epargne" ? "Épargne" : "Investissement"}
                    </span>
                    {item.original_item && item.original_item.currency !== "EUR" && (
                      <span className="text-[10px] text-slate-400 font-medium">
                        Original: {formatCurrency(item.original_item.balance, item.original_item.currency)}
                      </span>
                    )}
                  </div>
                </div>
              </div>
              <div className="shrink-0 whitespace-nowrap text-right pl-2">
                <span className="font-bold text-sm text-slate-900 block amount-blur">
                  {formatCurrency(item.balance_eur, "EUR")}
                </span>
                <span className="text-[11px] font-medium text-slate-400">
                  {formatRate(item.percentage, 1)}
                </span>
              </div>
            </div>
          ))
        ) : (
          flatItems.map((item: any) => (
            <div 
              key={item.id} 
              className="flex items-center justify-between p-3 rounded-xl border border-slate-100 hover:border-slate-200 hover:bg-slate-50/50 transition-all group/item"
            >
              <div className="flex min-w-0 items-center gap-3">
                <div 
                  className="h-3 w-3 rounded-full flex-shrink-0" 
                  style={{ backgroundColor: item.color }} 
                />
                <div className="min-w-0">
                  <span className="block truncate font-bold text-slate-800 text-sm group-hover/item:text-slate-900 transition-colors">
                    {item.name}
                  </span>
                  <div className="flex items-center gap-2 mt-0.5">
                    <span className="text-[10px] uppercase font-bold tracking-wider px-1.5 py-0.5 rounded bg-slate-100 text-slate-500">
                      {item.type === "courant" ? "Courant" : item.type === "epargne" ? "Épargne" : "Investissement"}
                    </span>
                    {item.original_item && item.original_item.currency !== "EUR" && (
                      <span className="text-[10px] text-slate-400 font-medium">
                        Original: {formatCurrency(item.original_item.balance, item.original_item.currency)}
                      </span>
                    )}
                  </div>
                </div>
              </div>
              <div className="shrink-0 whitespace-nowrap text-right pl-2">
                <span className="font-bold text-sm text-slate-900 block amount-blur">
                  {formatCurrency(item.balance_eur, "EUR")}
                </span>
                <span className="text-[11px] font-medium text-slate-400">
                  {formatRate(item.percentage, 1)}
                </span>
              </div>
            </div>
          ))
        )}
      </div>
    </>
  )
}
