import { AlertCircle, Clock, Plus, Trash2, TrendingUp } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { CompanyLogo } from "@/components/ui/CompanyLogo"
import { PriceChangesNotice } from "@/components/recurring/PriceChangesNotice"
import { Progress } from "@/components/ui/progress"
import { TabsContent } from "@/components/ui/tabs"
import { formatCurrency, frequencyLabel } from "@/lib/utils"
import type { RecurringTransactionsCtx } from "./useRecurringTransactions"

/** Onglet analyse : abonnements, investissements et autres flux récurrents. */
export function SubscriptionsTab({ ctx }: { ctx: RecurringTransactionsCtx }) {
  const { activeSubs, handleIgnoreDetection, handleOpenValidate, monthlyBreakdown, monthlyTotal, potentialSubs, safeFormat, setFlowSub, setSubTab, subTab, subsData } = ctx
  return (
    <>
      <TabsContent value="subscriptions" className="space-y-6 md:space-y-8">
         <PriceChangesNotice changes={subsData?.price_changes} />
         <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
           <div className="scroll-fade-x flex max-w-full items-center gap-1 overflow-x-auto p-1 bg-slate-100 rounded-xl w-fit [scrollbar-width:none] [&::-webkit-scrollbar]:hidden [&>button]:shrink-0">
             <Button 
              variant={subTab === "subscriptions" ? "white" : "ghost"} 
              size="sm" 
              className={`h-9 rounded-lg font-bold text-xs px-4 ${subTab === "subscriptions" ? "shadow-sm" : "text-slate-500 hover:text-slate-900"}`}
              onClick={() => setSubTab("subscriptions")}
             >
               Abonnements
             </Button>
             <Button 
              variant={subTab === "investments" ? "white" : "ghost"} 
              size="sm" 
              className={`rounded-lg font-bold text-xs px-4 ${subTab === "investments" ? "shadow-sm" : "text-slate-500 hover:text-slate-900"}`}
              onClick={() => setSubTab("investments")}
             >
               Investissements
             </Button>
             <Button 
              variant={subTab === "other" ? "white" : "ghost"} 
              size="sm" 
              className={`rounded-lg font-bold text-xs px-4 ${subTab === "other" ? "shadow-sm" : "text-slate-500 hover:text-slate-900"}`}
              onClick={() => setSubTab("other")}
             >
               Autres récurrences
             </Button>
           </div>
           <div className="text-[10px] font-black uppercase tracking-widest text-slate-400">
             {activeSubs.length} Confirmés • {potentialSubs.length} Potentiels
           </div>
         </div>

         <div className="grid grid-cols-2 gap-3 md:gap-6 md:grid-cols-3">
           <Card className="shadow-sm border-slate-100">
             <CardHeader className="pb-2">
               <CardDescription className="font-medium text-slate-500">
                  {subTab === "subscriptions" ? "Coût Mensuel Total" : subTab === "other" ? "Flux Mensuel" : "Versement Mensuel"}
               </CardDescription>
             </CardHeader>
             <CardContent>
               <CardTitle className="text-2xl md:text-3xl font-bold text-slate-900">
                 {formatCurrency(monthlyTotal)}
               </CardTitle>
               <p className="text-xs text-slate-400 mt-1">
                 {subTab === "subscriptions" ? "Prélevé automatiquement chaque mois" : subTab === "other" ? "Moyenne mensuelle des flux récurrents" : "Moyenne mensuelle investie"}
               </p>
             </CardContent>
           </Card>

           <Card className="shadow-sm border-slate-100">
             <CardHeader className="pb-2">
               <CardDescription className="font-medium text-slate-500">
                 {subTab === "subscriptions" ? "Impact Annuel" : subTab === "other" ? "Total Annuel" : "Total Annuel Projeté"}
               </CardDescription>
             </CardHeader>
             <CardContent>
               <CardTitle className="text-2xl md:text-3xl font-bold text-slate-900">
                 {formatCurrency(activeSubs.reduce((acc: number, s: any) => acc + s.annual_cost, 0))}
               </CardTitle>
               <p className="text-xs text-slate-400 mt-1">
                 {subTab === "subscriptions" ? "Budget total sur 12 mois" : subTab === "other" ? "Projection sur 12 mois" : "Objectif d'investissement annuel"}
               </p>
             </CardContent>
           </Card>

           <Card className="shadow-sm border-slate-100 col-span-2 md:col-span-1">
             <CardHeader className="pb-2">
               <CardDescription className="font-medium text-slate-500">
                 {subTab === "subscriptions" ? "Services actifs" : subTab === "other" ? "Récurrences actives" : "Plans d'investissement"}
               </CardDescription>
             </CardHeader>
             <CardContent>
               <CardTitle className="text-2xl md:text-3xl font-bold text-slate-900">
                 {activeSubs.filter((s: any) => s.status !== "lapsed").length}
               </CardTitle>
               <p className="text-xs text-slate-400 mt-1">{potentialSubs.length} détections en attente</p>
             </CardContent>
           </Card>
         </div>

         <div className="grid gap-6 lg:gap-8 lg:grid-cols-12">
           <div className={`${subTab === "other" ? "lg:col-span-12" : "lg:col-span-8"} space-y-6`}>
              <Card className="shadow-sm border-slate-100 overflow-hidden">
                <CardHeader className="border-b bg-slate-50/30">
                  <CardTitle className="text-lg">
                    {subTab === "subscriptions" ? "Abonnements confirmés" : subTab === "other" ? "Autres récurrences" : "Investissements programmés"}
                  </CardTitle>
                </CardHeader>
                <CardContent className="p-0">
                  <div className="divide-y">
                    {activeSubs.length === 0 ? (
                      <div className="p-12 text-center">
                        <Clock className="h-8 w-8 text-slate-200 mx-auto mb-3" />
                        <p className="text-sm font-bold text-slate-400 uppercase tracking-widest">Aucun élément</p>
                      </div>
                    ) : (
                      activeSubs.map((sub: any, i: number) => (
                        <div
                          key={i}
                          className={`p-4 flex items-center justify-between gap-3 hover:bg-slate-50 transition-colors group ${subTab === "investments" ? "cursor-pointer" : ""}`}
                          onClick={subTab === "investments" ? () => setFlowSub(sub) : undefined}
                        >
                          <div className="flex items-center gap-3 md:gap-4 min-w-0">
                            <CompanyLogo
                              ticker={sub.ticker}
                              name={sub.name}
                              logo={sub.logo}
                              className="h-10 w-10 md:h-12 md:w-12 rounded-2xl shrink-0 shadow-sm"
                            />
                            <div className="min-w-0">
                              <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5">
                                <p className="font-bold text-slate-900 break-words">{sub.name}</p>
                                {sub.status === "lapsed" ? (
                                  <Badge title="Aucun prélèvement depuis plus de deux échéances : à désactiver si l'abonnement est arrêté" className="bg-slate-100 text-slate-600 hover:bg-slate-100 border-none text-[9px] h-4 px-1.5 font-black uppercase">Plus prélevé ?</Badge>
                                ) : (
                                  <Badge className="bg-emerald-100 text-emerald-700 hover:bg-emerald-100 border-none text-[9px] h-4 px-1.5 font-black uppercase">Certifié</Badge>
                                )}
                              </div>
                              <div className="flex flex-wrap items-center gap-x-2 mt-0.5">
                                <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">{sub.category_name}</span>
                                <span className="text-slate-300">•</span>
                                <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">{frequencyLabel(sub.frequency)}</span>
                              </div>
                            </div>
                          </div>
                          <div className="text-right flex items-center gap-6 shrink-0">
                            <div className="hidden sm:block text-right">
                              <p className="text-[10px] text-slate-400 font-black uppercase tracking-widest">Prochain</p>
                              <p className="text-sm font-bold text-slate-700">
                                {safeFormat(sub.next_occurrence, "d MMM")}
                              </p>
                            </div>
                            <div>
                              <p className="text-base md:text-lg font-black text-slate-900 whitespace-nowrap tabular-nums">{formatCurrency(sub.amount)}</p>
                              <p className="text-[10px] font-bold text-slate-400 text-right whitespace-nowrap">
                                {subTab === "subscriptions" ? `${formatCurrency(sub.monthly_cost)}/mois` : subTab === "other" ? `${formatCurrency(sub.monthly_cost)}/mois` : "Versé"}
                              </p>
                            </div>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </CardContent>
              </Card>

              {potentialSubs.length > 0 && (
                <Card className={`shadow-sm border-amber-100 ${subTab === 'subscriptions' ? 'bg-amber-50/10' : 'bg-indigo-50/10 border-indigo-100'}`}>
                  <CardHeader className={`flex flex-row items-center justify-between border-b ${subTab === 'subscriptions' ? 'border-amber-100/50' : 'border-indigo-100/50'}`}>
                    <div>
                      <CardTitle className={`text-lg flex items-center gap-2 ${subTab === 'subscriptions' ? 'text-amber-900' : 'text-indigo-900'}`}>
                        {subTab === 'subscriptions' ? <AlertCircle className="h-5 w-5 text-amber-500" /> : <TrendingUp className="h-5 w-5 text-indigo-500" />}
                        Détections intelligentes
                      </CardTitle>
                      <CardDescription className={subTab === 'subscriptions' ? 'text-amber-700/70' : 'text-indigo-700/70'}>
                        {subTab === 'subscriptions' ? "Abonnements potentiels trouvés dans votre historique." : "Investissements réguliers détectés."}
                      </CardDescription>
                    </div>
                  </CardHeader>
                  <CardContent className="p-0">
                    <div className={`divide-y border-t ${subTab === 'subscriptions' ? 'border-amber-100' : 'border-indigo-100'}`}>
                      {potentialSubs.map((sub: any, i: number) => (
                        <div key={i} className="p-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between group">
                          <div className="flex items-center gap-3 md:gap-4 min-w-0">
                            <CompanyLogo
                              ticker={sub.ticker}
                              name={sub.name}
                              logo={sub.logo}
                              className="h-10 w-10 md:h-12 md:w-12 rounded-2xl shrink-0 shadow-sm"
                            />
                            <div className="min-w-0 flex-1">
                              <p className="font-bold text-slate-900 break-words">{sub.name}</p>
                              <div className="flex items-center gap-2 mt-0.5">
                                <span className={`text-[10px] font-black uppercase tracking-widest ${subTab === 'subscriptions' ? 'text-amber-600' : 'text-indigo-600'}`}>Récurrence détectée</span>
                              </div>
                            </div>
                          </div>
                          <div className="flex flex-wrap items-center justify-between gap-3 sm:justify-end sm:gap-4">
                            <div className="text-right">
                              <p className="text-lg font-black text-slate-900 whitespace-nowrap tabular-nums">{formatCurrency(sub.amount)}</p>
                              <p className="text-[10px] font-bold text-slate-400 uppercase">Valider ?</p>
                            </div>
                            <div className="flex items-center gap-2">
                              <Button size="sm" variant="ghost" aria-label="Ignorer" className="text-slate-400 hover:text-red-600 h-10 w-10 px-2 md:h-8 md:w-auto" onClick={() => handleIgnoreDetection(sub)}>
                                <Trash2 className="h-3.5 w-3.5" />
                              </Button>
                              {subTab === "subscriptions" && (
                                <Button size="sm" variant="outline" className="border-slate-200 text-slate-600 hover:bg-slate-100 rounded-xl font-bold h-10 md:h-8 text-xs md:text-[11px]" onClick={() => handleOpenValidate(sub, true)}>
                                  Invest.
                                </Button>
                              )}
                              <Button size="sm" variant="outline" className={`rounded-xl font-bold h-10 md:h-8 text-xs md:text-[11px] ${subTab === 'subscriptions' ? 'border-amber-200 text-amber-700 hover:bg-amber-100' : 'border-indigo-200 text-indigo-700 hover:bg-indigo-100'}`} onClick={() => handleOpenValidate(sub, subTab === "investments")}>
                                Confirmer
                              </Button>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}
           </div>

           {subTab !== "other" && <div className="lg:col-span-4 space-y-6">
              <Card className="shadow-sm border-slate-100">
                <CardHeader className="border-b pb-4">
                  <CardTitle className="text-lg">Répartition mensuelle</CardTitle>
                  {monthlyTotal > 0 && (
                    <CardDescription>
                      {subTab === "subscriptions" ? "Part de chaque abonnement" : "Part de chaque plan"} dans les {formatCurrency(monthlyTotal)} par mois
                    </CardDescription>
                  )}
                </CardHeader>
                <CardContent className="p-4 md:p-6">
                  {monthlyBreakdown.length === 0 || monthlyTotal <= 0 ? (
                    <p className="text-sm text-slate-400">Aucun montant mensuel à répartir.</p>
                  ) : (
                    <ul className="space-y-4">
                      {monthlyBreakdown.map((sub: any) => {
                        const share = (sub.monthly_cost / monthlyTotal) * 100
                        return (
                          <li key={sub.name} className="space-y-1.5">
                            <div className="flex items-baseline justify-between gap-3 text-sm">
                              <span className="truncate font-medium text-slate-700">{sub.name}</span>
                              <span className="shrink-0 tabular-nums">
                                <span className="font-semibold text-slate-900">{formatCurrency(sub.monthly_cost)}</span>
                                <span className="ml-2 text-xs text-slate-400">{Math.round(share)} %</span>
                              </span>
                            </div>
                            <Progress value={share} className="h-1.5 bg-slate-100" indicatorClassName={subTab === "subscriptions" ? "bg-blue-500" : "bg-indigo-500"} />
                          </li>
                        )
                      })}
                    </ul>
                  )}
                </CardContent>
              </Card>
           </div>}
         </div>
      </TabsContent>
    </>
  )
}
