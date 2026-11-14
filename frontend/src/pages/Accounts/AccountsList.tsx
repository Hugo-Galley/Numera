import { AccountLogo } from "@/components/ui/AccountLogo"
import { Archive, ArrowDown, ArrowRight, ArrowUp, Star } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Link } from "react-router-dom"
import { useTranslation } from "react-i18next"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { formatCurrency, formatRate } from "@/lib/utils"
import type { AccountsCtx } from "./useAccounts"

/** Liste des comptes actifs (cartes mobile, tableau bureau). */
export function AccountsList({ ctx }: { ctx: AccountsCtx }) {
  const { t } = useTranslation("accounts")
  const { t: tc } = useTranslation()
  const { getTypeIcon, getTypeLabel, handleDeleteAccount, handleSort, handleToggleMain, loading, openEdit, sortField, sortOrder, sortedAccounts } = ctx
  return (
    <>
      <Card>
        <CardHeader>
          <CardTitle>{t("list.title")}</CardTitle>
          <CardDescription>{t("list.subtitle")}</CardDescription>
        </CardHeader>
        <CardContent className="px-3 sm:px-6">
          <div className="space-y-3 md:hidden">
            {loading ? (
              <p className="py-8 text-center text-muted-foreground">{t("list.loading")}</p>
            ) : sortedAccounts.length === 0 ? (
              <p className="py-8 text-center text-muted-foreground">{t("list.empty")}</p>
            ) : (
              sortedAccounts.map((account) => (
                <div key={account.id} className="rounded-xl border bg-white p-3">
                  <div className="flex items-start gap-1">
                    <Button
                      variant="ghost"
                      size="icon"
                      aria-label={t("list.mainAccount")}
                      className={`h-10 w-10 shrink-0 ${account.is_main ? 'text-amber-500 hover:text-amber-600' : 'text-slate-300 hover:text-amber-500'}`}
                      onClick={() => handleToggleMain(account.id, !!account.is_main)}
                    >
                      <Star className={`h-5 w-5 ${account.is_main ? 'fill-current' : ''}`} />
                    </Button>
                    <Link to={`/accounts/${account.id}`} className="min-w-0 flex-1 py-1">
                      <p className="flex items-center gap-2 wrap-break-word font-semibold leading-tight">
                        <AccountLogo accountId={account.id} logo={account.logo ?? null} className="h-6 w-6" />
                        {account.name}
                      </p>
                      <div className="mt-1 flex flex-wrap items-center gap-x-2 text-sm text-muted-foreground">
                        {getTypeIcon(account.type)}
                        <span>{getTypeLabel(account.type)}</span>
                        <span>· {account.currency}</span>
                      </div>
                      <p className="mt-1 font-semibold tabular-nums amount-blur">{formatCurrency(account.balance ?? 0, account.currency)}</p>
                    </Link>
                    <Badge variant={account.active ? "outline" : "secondary"} className="mt-2 shrink-0">
                      {account.active ? t("list.active") : t("list.inactive")}
                    </Badge>
                  </div>
                  <div className="mt-2 flex flex-wrap items-center gap-2 pl-1">
                    {/* Établissement masqué quand il répète le nom du compte (« Boursorama / Boursorama ») */}
                    {account.institution && account.institution.trim().toLowerCase() !== account.name.trim().toLowerCase() && (
                      <Badge variant="secondary" className="bg-slate-50 font-semibold text-slate-700 border-slate-200">
                        {account.institution}
                      </Badge>
                    )}
                    {account.type === "assurance_vie" && (account.fonds_euros_pct != null || account.fonds_investis_pct != null) && (
                      <Badge variant="secondary" className="bg-slate-100 font-medium text-slate-700">
                        {t("list.euroInvested", { euros: formatRate(account.fonds_euros_pct || 0, 1), invested: formatRate(account.fonds_investis_pct || 0, 1) })}
                      </Badge>
                    )}
                  </div>
                  <div className="mt-3 flex items-center gap-2">
                    <Button asChild className="h-10 flex-1 bg-slate-900 text-white hover:bg-slate-800">
                      <Link to={`/accounts/${account.id}`}>{t("list.viewDetails")} <ArrowRight className="ml-2 h-4 w-4" /></Link>
                    </Button>
                    <Button
                      variant="outline"
                      className="h-10"
                      onClick={() => openEdit(account)}
                    >
                      {tc("actions.edit")}
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      aria-label={t("list.archive")} title={t("list.archive")}
                      className="h-10 w-10 text-rose-600 hover:text-rose-700"
                      onClick={() => handleDeleteAccount(account.id)}
                    >
                      <Archive className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              ))
            )}
          </div>
          <div className="hidden rounded-md border overflow-x-auto md:block">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="cursor-pointer hover:bg-slate-50 transition-colors" onClick={() => handleSort("name")}>
                    <div className="flex items-center gap-2">
                      {t("list.columns.name")}
                      {sortField === "name" && (sortOrder === "asc" ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />)}
                    </div>
                  </TableHead>
                  <TableHead className="cursor-pointer hover:bg-slate-50 transition-colors" onClick={() => handleSort("institution")}>
                    <div className="flex items-center gap-2">
                      {t("list.columns.institution")}
                      {sortField === "institution" && (sortOrder === "asc" ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />)}
                    </div>
                  </TableHead>
                  <TableHead className="cursor-pointer hover:bg-slate-50 transition-colors" onClick={() => handleSort("type")}>
                    <div className="flex items-center gap-2">
                      {t("list.columns.type")}
                      {sortField === "type" && (sortOrder === "asc" ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />)}
                    </div>
                  </TableHead>
                  <TableHead className="cursor-pointer hover:bg-slate-50 transition-colors" onClick={() => handleSort("currency")}>
                    <div className="flex items-center gap-2">
                      {t("list.columns.currency")}
                      {sortField === "currency" && (sortOrder === "asc" ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />)}
                    </div>
                  </TableHead>
                  <TableHead className="text-right">{t("list.columns.balance")}</TableHead>
                  <TableHead>{t("list.columns.status")}</TableHead>
                  <TableHead className="text-right">{t("list.columns.actions")}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {loading ? (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center py-8 text-muted-foreground">
                      {t("list.loading")}
                    </TableCell>
                  </TableRow>
                ) : sortedAccounts.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center py-8 text-muted-foreground">
                      {t("list.empty")}
                    </TableCell>
                  </TableRow>
                ) : (
                  sortedAccounts.map((account) => (
                    <TableRow key={account.id}>
                      <TableCell className="font-medium">
                        <div className="flex items-center gap-2">
                          <Button aria-label={t("list.favorite")} 
                            variant="ghost" 
                            size="icon" 
                            className={`h-6 w-6 ${account.is_main ? 'text-amber-500 hover:text-amber-600' : 'text-slate-300 hover:text-amber-500'}`}
                            onClick={() => handleToggleMain(account.id, !!account.is_main)}
                          >
                            <Star className={`h-4 w-4 ${account.is_main ? 'fill-current' : ''}`} />
                          </Button>
                          <AccountLogo accountId={account.id} logo={account.logo ?? null} className="h-6 w-6" />
                          {account.name}
                        </div>
                      </TableCell>
                      <TableCell>
                        {account.institution ? (
                          <Badge variant="secondary" className="font-semibold bg-slate-50 text-slate-700 border-slate-200">
                            {account.institution}
                          </Badge>
                        ) : (
                          <span className="text-slate-400 text-xs italic">—</span>
                        )}
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          {getTypeIcon(account.type)}
                          <span className="capitalize">{getTypeLabel(account.type)}</span>
                          {account.type === "assurance_vie" && (account.fonds_euros_pct !== undefined && account.fonds_euros_pct !== null || account.fonds_investis_pct !== undefined && account.fonds_investis_pct !== null) && (
                            <Badge variant="secondary" className="ml-2 font-medium bg-slate-100 text-slate-700">
                              {t("list.euroInvested", { euros: formatRate(account.fonds_euros_pct || 0, 1), invested: formatRate(account.fonds_investis_pct || 0, 1) })}
                            </Badge>
                          )}
                        </div>
                      </TableCell>
                      <TableCell>{account.currency}</TableCell>
                      <TableCell className="text-right font-semibold tabular-nums whitespace-nowrap amount-blur">
                        {formatCurrency(account.balance ?? 0, account.currency)}
                      </TableCell>
                      <TableCell>
                        <Badge variant={account.active ? "outline" : "secondary"}>
                          {account.active ? t("list.active") : t("list.inactive")}
                        </Badge>
                      </TableCell>
                        <TableCell className="text-right">
                          <div className="flex items-center justify-end gap-2">
                            <Button 
                              variant="outline" 
                              size="sm"
                              onClick={() => openEdit(account)}
                            >
                              {tc("actions.edit")}
                            </Button>
                            <Button variant="ghost" size="sm" asChild>
                              <Link to={`/accounts/${account.id}`}>
                                {t("list.viewDetails")} <ArrowRight className="ml-2 h-4 w-4" />
                              </Link>
                            </Button>
                            <Button aria-label={t("list.archive")} title={t("list.archive")}
                              variant="ghost"
                              size="icon"
                              className="text-rose-600 hover:text-rose-700"
                              onClick={() => handleDeleteAccount(account.id)}
                            >
                              <Archive className="h-4 w-4" />
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
    </>
  )
}
