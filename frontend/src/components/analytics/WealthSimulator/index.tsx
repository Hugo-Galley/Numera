import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { RefreshCw, TrendingUp } from "lucide-react"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { WealthSimulatorProps } from "./types"
import { useWealthSimulator } from "./useWealthSimulator"
import { BaseTab } from "./BaseTab"
import { AllocationTab } from "./AllocationTab"
import { AdvancedTab } from "./AdvancedTab"
import { EventsTab } from "./EventsTab"
import { DetailTable } from "./DetailTable"
import { SimulatorKpis } from "./SimulatorKpis"
import { SimulatorChart } from "./SimulatorChart"
import { AssetDialog } from "./AssetDialog"

export function WealthSimulator({ initialCapitalDefault = 10000 }: WealthSimulatorProps) {
  const ctx = useWealthSimulator(initialCapitalDefault)
  const { activeEventsCount, computedReturn, computedVolatility, isVolatile, loading, params, showInflationAdjusted, useAllocation } = ctx
  return (
    <Card className="w-full border-slate-200 shadow-sm">
      <CardHeader className="p-4 pb-3 md:p-6 md:pb-4 border-b border-slate-100 bg-slate-50/50">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex min-w-0 items-center gap-2.5">
            <div className="shrink-0 p-2 bg-indigo-50 text-indigo-600 rounded-lg">
              <TrendingUp className="h-5 w-5" />
            </div>
            <div>
              <CardTitle className="text-lg font-bold text-slate-900">Simulateur de Patrimoine Avancé</CardTitle>
              <CardDescription>
                Projetez votre stratégie d'investissement avec volatilité, inflation, fiscalité et accidents de parcours.
              </CardDescription>
            </div>
          </div>
          <div className="flex items-center gap-2 self-start md:self-auto">
            {loading && <RefreshCw className="h-4 w-4 animate-spin text-slate-400" />}
            {isVolatile && <Badge className="bg-purple-50 text-purple-700 border-purple-200">Monte Carlo Actif</Badge>}
            {showInflationAdjusted && <Badge className="bg-red-50 text-red-700 border-red-200">Euros Constants</Badge>}
          </div>
        </div>
      </CardHeader>

      <Tabs defaultValue="base" className="w-full">
        <CardContent className="p-4 pt-4 md:p-6 md:pt-6 space-y-6">
          
          {/* 1. CHOIX DE PARAMETRES EN HAUT (TabsList) */}
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-100 pb-4">
            <TabsList className="bg-slate-100 p-1 rounded-lg shrink-0 flex w-full md:w-auto justify-start overflow-x-auto flex-nowrap gap-0.5 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
              <TabsTrigger value="base" className="text-xs py-2.5 md:py-1.5 px-3 whitespace-nowrap">Général</TabsTrigger>
              <TabsTrigger value="allocation" className="text-xs py-2.5 md:py-1.5 px-3 whitespace-nowrap">Allocation d'Actifs</TabsTrigger>
              <TabsTrigger value="advanced" className="text-xs py-2.5 md:py-1.5 px-3 whitespace-nowrap">Fiscalité & Risque</TabsTrigger>
              <TabsTrigger value="events" className="text-xs py-2.5 md:py-1.5 px-3 relative whitespace-nowrap">
                Événements de Vie
                {activeEventsCount > 0 && (
                  <span className="absolute -top-1 -right-1 flex h-4 w-4 items-center justify-center rounded-full bg-indigo-600 text-[9px] font-bold text-white">
                    {activeEventsCount}
                  </span>
                )}
              </TabsTrigger>
            </TabsList>
            
            <div className="flex items-center gap-2 text-xs text-slate-500 font-semibold bg-indigo-50/50 border border-indigo-100/50 rounded-lg py-1.5 px-3">
              <span>Configuration active : </span>
              {useAllocation ? (
                <span className="text-indigo-700 font-bold">Allocation d'actifs ({computedReturn}% rdt / {computedVolatility}% vol)</span>
              ) : (
                <span className="text-indigo-700 font-bold">Saisie manuelle ({params.annual_return_pct}% rdt / {params.volatility_pct}% vol)</span>
              )}
            </div>
          </div>

          {/* 2. GRILLE PRINCIPALE (A GAUCHE: INPUTS + TABLEAU DET, A DROITE: KPIs + GRAPHIQUE) */}
          <div className="grid grid-cols-1 xl:grid-cols-12 gap-8 items-start">
            
            {/* COLONNE GAUCHE (5 COLS) : CONTROLEURS + TABLEAU DET */}
            <div className="xl:col-span-5 space-y-6">
              
              {/* CADRE DES INPUTS DE L'ONGLET ACTIF */}
              <div className="bg-slate-50/40 p-4 rounded-xl border border-slate-100 shadow-sm space-y-4">
                
                <BaseTab ctx={ctx} />

                <AllocationTab ctx={ctx} />

                <AdvancedTab ctx={ctx} />

                <EventsTab ctx={ctx} />
              </div>

              <DetailTable ctx={ctx} />

            </div>

            {/* COLONNE DROITE (7 COLS) : KPIs + GRAPHIQUE + INFOS */}
            <div className="xl:col-span-7 space-y-6">
              
              <SimulatorKpis ctx={ctx} />

              <SimulatorChart ctx={ctx} />

            </div>

          </div>
        </CardContent>
      </Tabs>

      <AssetDialog ctx={ctx} />

    </Card>
  )
}
