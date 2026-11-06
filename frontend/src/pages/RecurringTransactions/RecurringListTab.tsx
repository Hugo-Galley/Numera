import i18n from "i18next"
import { useTranslation } from "react-i18next"
import { appLocale, dateLocale } from "@/i18n/locale"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { CheckCircle2, Pencil, Sparkles, Trash2, XCircle } from "lucide-react"
import { Checkbox } from "@/components/ui/checkbox"
import { CompanyLogo } from "@/components/ui/CompanyLogo"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { TabsContent } from "@/components/ui/tabs"
import { format } from "date-fns"
import { frequencyLabel } from "@/lib/utils"
import type { RecurringTransactionsCtx } from "./useRecurringTransactions"

/** Onglet liste : toutes les récurrences (cartes mobile, tableau bureau). */
export function RecurringListTab({ ctx }: { ctx: RecurringTransactionsCtx }) {
  const { t } = useTranslation("recurring")
  const { accounts, handleDelete, handleOpenEdit, loading, recurringTxs, toggleActive } = ctx
  return (
    <>
      <TabsContent value="recurring" className="space-y-6">
        <Card className="shadow-sm border-slate-100">
          <CardHeader className="pb-4">
            <CardTitle className="text-lg">{t("recurringListTab.toutesLesRecurrences")}</CardTitle>
            <CardDescription>
              {recurringTxs.length} récurrence(s) configurée(s) au total.
            </CardDescription>
          </CardHeader>
          <CardContent className="p-0">
            <div className="md:hidden divide-y">
              {loading ? (
                <p className="text-center py-10 text-slate-400 italic text-sm">{t("recurringListTab.chargementDesRecurrences")}</p>
              ) : recurringTxs.length === 0 ? (
                <p className="text-center py-10 text-slate-400 italic text-sm">{t("recurringListTab.aucuneTransactionRecurrenteConfiguree")}</p>
              ) : (
                recurringTxs.map((tx) => {
                  const positive = tx.type === "Entree" || tx.type === "Interets" || tx.type === "versement" || tx.type === "dividende"
                  return (
                    <div key={tx.id} className={`p-4 space-y-3 ${tx.is_active ? "" : "opacity-60"}`}>
                      <div className="flex items-start gap-3">
                        <CompanyLogo
                          ticker={tx.ticker || undefined}
                          name={tx.name}
                          isin={tx.isin || undefined}
                          logo={tx.logo}
                          className="h-10 w-10 rounded-lg shadow-2xs shrink-0"
                        />
                        <div className="min-w-0 flex-1">
                          <p className="font-bold text-slate-900 text-sm break-words">{tx.name}</p>
                          <p className="text-xs text-slate-500 break-words">
                            {accounts.find(a => a.id === tx.account_id)?.name}
                            {tx.transfer_to_account_id && (
                              <span className="text-indigo-600"> → {accounts.find(a => a.id === tx.transfer_to_account_id)?.name}</span>
                            )}
                            {tx.quantity != null && tx.quantity > 0 && ` • ${i18n.t("misc.shares", { ns: "recurring", count: tx.quantity })}${tx.unit_price ? i18n.t("misc.atPrice", { ns: "recurring", price: tx.unit_price }) : ""}`}
                          </p>
                        </div>
                        <p className={`font-black text-base whitespace-nowrap tabular-nums ${positive ? "text-emerald-600" : "text-slate-900"}`}>
                          {(tx.type === "Sortie" || tx.type === "retrait") ? "-" : "+"}
                          {tx.amount.toLocaleString(appLocale(), { style: "currency", currency: tx.currency })}
                        </p>
                      </div>
                      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-slate-600">
                        <Badge variant={positive ? "default" : "secondary"} className="text-[10px] h-5">{tx.type}</Badge>
                        <span className="font-medium">{i18n.t("misc.dayOf", { ns: "recurring", frequency: frequencyLabel(tx.frequency), day: tx.day_of_month })}</span>
                        <span className="text-slate-400">
                          {i18n.t("misc.lastGenerated", { ns: "recurring", date: tx.last_generated_date ? format(new Date(tx.last_generated_date), "dd MMM yyyy", { locale: dateLocale() }) : i18n.t("misc.none", { ns: "recurring" }) })}
                        </span>
                        {tx.excluded_months && tx.excluded_months.length > 0 && (
                          <Badge variant="outline" className="text-[9px] h-4 px-1.5 text-amber-700 border-amber-200 bg-amber-50">
                            {i18n.t("misc.excludedMonths", { ns: "recurring", count: tx.excluded_months.length })}
                          </Badge>
                        )}
                      </div>
                      <div className="flex items-center justify-between">
                        <label className="flex min-h-10 items-center gap-2 text-sm text-slate-700">
                          <Checkbox checked={tx.is_active} onCheckedChange={() => toggleActive(tx)} className="rounded-md h-5 w-5" />
                          Actif
                          {tx.auto_generate && <span className="inline-flex items-center gap-1 text-xs text-emerald-600"><CheckCircle2 className="h-3.5 w-3.5" />{t("recurringListTab.auto")}</span>}
                        </label>
                        <div className="flex gap-1">
                          <Button variant="ghost" size="icon" className="h-10 w-10 text-slate-500" onClick={() => handleOpenEdit(tx)} aria-label={t("recurringListTab.modifier")}>
                            <Pencil className="h-4 w-4" />
                          </Button>
                          <Button variant="ghost" size="icon" className="h-10 w-10 text-slate-500 hover:text-red-600" onClick={() => handleDelete(tx.id)} aria-label={t("recurringListTab.supprimer")}>
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </div>
                    </div>
                  )
                })
              )}
            </div>
            <div className="hidden md:block">
            <Table>
              <TableHeader className="bg-slate-50/50">
                <TableRow>
                  <TableHead>{t("recurringListTab.nom")}</TableHead>
                  <TableHead>{t("recurringListTab.type")}</TableHead>
                  <TableHead>{t("recurringListTab.montant")}</TableHead>
                  <TableHead>{t("recurringListTab.frequence")}</TableHead>
                  <TableHead>{t("recurringListTab.derniereGen")}</TableHead>
                  <TableHead className="text-center">{t("recurringListTab.auto")}</TableHead>
                  <TableHead className="text-center">{t("recurringListTab.actif")}</TableHead>
                  <TableHead className="text-right">{t("recurringListTab.actions")}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {loading ? (
                  <TableRow>
                    <TableCell colSpan={8} className="text-center py-12 text-slate-400 italic">
                      {t("recurringListTab.chargementDesRecurrences")}
                    </TableCell>
                  </TableRow>
                ) : recurringTxs.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={8} className="text-center py-12 text-slate-400 italic">
                      {t("recurringListTab.aucuneTransactionRecurrenteConfiguree")}
                    </TableCell>
                  </TableRow>
                ) : (
                  recurringTxs.map((tx) => (
                    <TableRow key={tx.id} className="group hover:bg-slate-50 transition-colors">
                      <TableCell>
                        <div className="flex items-center gap-3">
                          <CompanyLogo
                            ticker={tx.ticker || undefined}
                            name={tx.name}
                            isin={tx.isin || undefined}
                            logo={tx.logo}
                            className="h-8 w-8 rounded-lg shadow-2xs shrink-0"
                          />
                          <div className="flex flex-col min-w-0">
                            <span className="font-bold text-slate-900 text-sm truncate max-w-[260px]" title={tx.name}>
                              {tx.name}
                            </span>
                            <div className="text-[11px] text-slate-500 font-medium mt-0.5 flex items-center gap-1.5 flex-wrap">
                              {tx.ticker && (
                                <>
                                  <span className="font-mono text-slate-400 text-[10px] font-semibold uppercase">{tx.ticker}</span>
                                  <span className="text-slate-300">•</span>
                                </>
                              )}
                              <span className="text-slate-600">{accounts.find(a => a.id === tx.account_id)?.name}</span>
                              {tx.transfer_to_account_id && (
                                <span className="font-medium text-indigo-600">
                                  → {accounts.find(a => a.id === tx.transfer_to_account_id)?.name}
                                  {tx.transfer_credit_day ? i18n.t("misc.arrivalDay", { ns: "recurring", day: tx.transfer_credit_day }) : ""}
                                </span>
                              )}
                              <span>•</span>
                              {tx.quantity != null && tx.quantity > 0 ? (
                                <>
                                  <span>•</span>
                                  <span className="font-semibold text-slate-700 font-mono">
                                    {i18n.t("misc.shares", { ns: "recurring", count: tx.quantity })}
                                    {tx.unit_price ? i18n.t("misc.atPrice", { ns: "recurring", price: tx.unit_price }) : ""}
                                  </span>
                                </>
                              ) : tx.ticker ? (
                                <>
                                  <span>•</span>
                                  <span className="text-[9px] text-blue-700 font-semibold bg-blue-50 px-1.5 py-0.5 rounded border border-blue-200/60 inline-flex items-center gap-1">
                                    <Sparkles className="h-2.5 w-2.5 text-blue-500" />
                                    {t("recurringListTab.partsAuto")}
                                    {tx.unit_price ? ` (~${(tx.amount / tx.unit_price).toFixed(2)}p)` : ""}
                                  </span>
                                </>
                              ) : null}
                            </div>
                          </div>
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge variant={(tx.type === "Entree" || tx.type === "Interets" || tx.type === "versement" || tx.type === "dividende") ? "default" : "secondary"} className="text-[10px] h-5">
                          {tx.type}
                        </Badge>
                      </TableCell>
                      <TableCell className={`font-black ${(tx.type === "Entree" || tx.type === "Interets" || tx.type === "versement" || tx.type === "dividende") ? "text-emerald-600" : "text-slate-900"}`}>
                        {(tx.type === "Sortie" || tx.type === "retrait") ? "-" : "+"}
                        {tx.amount.toLocaleString(appLocale(), { style: "currency", currency: tx.currency })}
                      </TableCell>
                      <TableCell>
                        <div className="text-sm font-medium text-slate-700">{frequencyLabel(tx.frequency)}</div>
                        <div className="text-[10px] text-slate-400 font-bold">JOUR {tx.day_of_month}</div>
                        {tx.excluded_months && tx.excluded_months.length > 0 && (
                          <div className="mt-1">
                            <Badge variant="outline" className="text-[9px] h-4 px-1.5 text-amber-700 border-amber-200 bg-amber-50 font-medium whitespace-nowrap">
                              {i18n.t("misc.excludedMonths", { ns: "recurring", count: tx.excluded_months.length })}
                            </Badge>
                          </div>
                        )}
                      </TableCell>
                      <TableCell>
                        <div className="text-sm text-slate-600">
                          {tx.last_generated_date 
                            ? format(new Date(tx.last_generated_date), "dd MMM yyyy", { locale: dateLocale() })
                            : t("recurringListTab.aucune")
                          }
                        </div>
                      </TableCell>
                      <TableCell className="text-center">
                        {tx.auto_generate ? (
                          <CheckCircle2 className="h-4 w-4 text-emerald-500 mx-auto" />
                        ) : (
                          <XCircle className="h-4 w-4 text-slate-200 mx-auto" />
                        )}
                      </TableCell>
                      <TableCell className="text-center">
                        <Checkbox 
                          checked={tx.is_active} 
                          onCheckedChange={() => toggleActive(tx)} 
                          className="rounded-md"
                        />
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-1">
                          <Button aria-label={t("recurringListTab.modifier")} variant="ghost" size="icon" className="h-8 w-8 text-slate-400 hover:text-slate-900" onClick={() => handleOpenEdit(tx)}>
                            <Pencil className="h-4 w-4" />
                          </Button>
                          <Button aria-label={t("recurringListTab.supprimer")} variant="ghost" size="icon" className="h-8 w-8 text-slate-400 hover:text-red-600" onClick={() => handleDelete(tx.id)}>
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
            </div>
          </CardContent>
        </Card>
      </TabsContent>
    </>
  )
}
