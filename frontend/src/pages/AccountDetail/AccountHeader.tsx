import { AccountLogo } from "@/components/ui/AccountLogo"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { ChevronRight, Scale, Upload, Wallet } from "lucide-react"
import { Link } from "react-router-dom"
import type { AccountDetailView } from "./useAccountDetail"
import { TransactionDialog } from "./TransactionDialog"
import { InvestmentTxDialog } from "./InvestmentTxDialog"
import { SnapshotDialog } from "./SnapshotDialog"
import { ZeroPointDialog } from "./ZeroPointDialog"

/** En-tête : fil d'Ariane, nom du compte et boutons d'action (avec leurs dialogues). */
export function AccountHeader({ ctx }: { ctx: AccountDetailView }) {
  const { account, id, isInvestment, setImportOpen, setReconcileOpen } = ctx
  return (
    <>
      <div className="flex flex-col gap-4">
        <div className="flex min-w-0 items-center gap-2 text-sm text-slate-500">
          <Link to="/accounts" className="hover:text-slate-900 transition-colors">Comptes</Link>
          <ChevronRight className="h-3 w-3" />
          <span className="truncate text-slate-900 font-medium">{account.name}</span>
        </div>

        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center gap-3 sm:gap-4">
            {account.logo ? (
              <AccountLogo accountId={account.id} logo={account.logo} className="hidden h-14 w-14 rounded-2xl sm:flex" />
            ) : (
              <div className="theme-island hidden h-14 w-14 shrink-0 bg-slate-900 rounded-2xl sm:flex items-center justify-center text-white shadow-lg">
                <Wallet className="h-7 w-7" />
              </div>
            )}
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <h1 className="break-words text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl">{account.name}</h1>
                <Badge className="bg-slate-100 text-slate-600 border-none capitalize">
                  {account.type === "assurance_vie" ? "Assurance-Vie" : account.type}
                </Badge>
              </div>
              <p className="text-slate-500">Flux financiers en {account.currency}</p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2 max-sm:[&>button]:h-11 max-sm:[&>button]:flex-1">
            {!isInvestment ? (
              <>
              <Button variant="outline" className="h-11 w-full sm:h-10 sm:w-auto" onClick={() => setReconcileOpen(true)}>
                <Scale className="h-4 w-4 mr-2" /> Rapprocher
              </Button>
              <Button variant="outline" className="h-11 w-full sm:h-10 sm:w-auto" onClick={() => setImportOpen(true)}>
                <Upload className="h-4 w-4 mr-2" /> Importer
              </Button>
              <TransactionDialog ctx={ctx} />
              </>
            ) : (
              <>
                <InvestmentTxDialog ctx={ctx} />
                <SnapshotDialog ctx={ctx} />
                <ZeroPointDialog ctx={ctx} />
              </>
            )}
          </div>
        </div>
      </div>
    </>
  )
}
