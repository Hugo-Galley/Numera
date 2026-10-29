import { DividendsCard } from "@/components/investments/DividendsCard"
import { HoldingsTable } from "@/components/investments/HoldingsTable"
import { PortfolioSummary } from "@/components/investments/PortfolioSummary"
import { toast } from "sonner"
import type { AccountDetailView } from "./useAccountDetail"
import { InvestmentFlowsCard } from "./InvestmentFlowsCard"
import { SnapshotsCard } from "./SnapshotsCard"
import { patchAccountsById } from "@/lib/api/accounts"

/** Section d'un compte d'investissement : positions, synthèse, dividendes, flux et snapshots. */
export function InvestmentSection({ ctx }: { ctx: AccountDetailView }) {
  const { account, handleAddDividend, holdings, id, isInvestment, loadData } = ctx
  return (
    <>
      {isInvestment && account && (
        <div className="space-y-8">
          {/* Positions Actuelles (Nombre de parts & Cotations en Direct) */}
          <HoldingsTable
            accountId={account.id}
            accountName={account.name}
            holdings={holdings}
            onRefresh={loadData}
            onAddDividend={handleAddDividend}
          />

          {isInvestment && (
            <div className="flex flex-col gap-2 rounded-lg border bg-white p-3 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p className="text-sm font-semibold text-slate-900">Valorisation du compte</p>
                <p className="text-xs text-slate-500">
                  {account.valuation_mode === "snapshot"
                    ? "La valeur vient de tes relevés (snapshots) : pas de suivi des positions pour le calcul."
                    : "La valeur est calculée : positions × cours + espèces. Les relevés servent à vérifier."}
                </p>
              </div>
              <div className="flex shrink-0 items-center gap-1 rounded-lg bg-slate-100 p-1">
                {([["positions", "Positions × cours"], ["snapshot", "Relevés"]] as const).map(([mode, label]) => (
                  <button
                    key={mode}
                    onClick={async () => {
                      if ((account.valuation_mode ?? "positions") === mode) return
                      try {
                        await patchAccountsById(account.id, { valuation_mode: mode })
                        toast.success(mode === "snapshot" ? "Valorisation par relevés" : "Valorisation par positions")
                        loadData({ quiet: true })
                      } catch (err: any) {
                        toast.error(err?.message || "Impossible de changer la valorisation")
                      }
                    }}
                    className={`rounded-md px-3 py-1 text-xs font-semibold transition-all ${
                      (account.valuation_mode ?? "positions") === mode ? "bg-white text-slate-900 shadow-sm" : "text-slate-500 hover:text-slate-700"
                    }`}
                  >
                    {label}
                  </button>
                ))}
              </div>
            </div>
          )}

          <PortfolioSummary accountId={account.id} reloadKey={holdings} />

          <DividendsCard accountId={account.id} reloadKey={holdings} onChanged={loadData} />

          <div className="grid gap-8 lg:grid-cols-2">
           <InvestmentFlowsCard ctx={ctx} />
           <SnapshotsCard ctx={ctx} />
          </div>
        </div>
      )}
    </>
  )
}
