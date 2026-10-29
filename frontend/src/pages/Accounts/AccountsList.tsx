import { AccountLogo } from "@/components/ui/AccountLogo"
import { Archive, ArrowDown, ArrowRight, ArrowUp, Star } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Link } from "react-router-dom"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { formatCurrency, formatRate } from "@/lib/utils"
import type { AccountsCtx } from "./useAccounts"

/** Liste des comptes actifs (cartes mobile, tableau bureau). */
export function AccountsList({ ctx }: { ctx: AccountsCtx }) {
  const { accounts, getTypeIcon, getTypeLabel, handleDeleteAccount, handleSort, handleToggleMain, loading, openEdit, sortField, sortOrder, sortedAccounts } = ctx
  return (
    <>
      <Card>
        <CardHeader>
          <CardTitle>Liste des comptes</CardTitle>
          <CardDescription>Tous vos comptes actifs.</CardDescription>
        </CardHeader>
        <CardContent className="px-3 sm:px-6">
          <div className="space-y-3 md:hidden">
            {loading ? (
              <p className="py-8 text-center text-muted-foreground">Chargement...</p>
            ) : sortedAccounts.length === 0 ? (
              <p className="py-8 text-center text-muted-foreground">Aucun compte trouvé.</p>
            ) : (
              sortedAccounts.map((account) => (
                <div key={account.id} className="rounded-xl border bg-white p-3">
                  <div className="flex items-start gap-1">
                    <Button
                      variant="ghost"
                      size="icon"
                      aria-label="Compte principal"
                      className={`h-10 w-10 shrink-0 ${account.is_main ? 'text-amber-500 hover:text-amber-600' : 'text-slate-300 hover:text-amber-500'}`}
                      onClick={() => handleToggleMain(account.id, !!account.is_main)}
                    >
                      <Star className={`h-5 w-5 ${account.is_main ? 'fill-current' : ''}`} />
                    </Button>
                    <Link to={`/accounts/${account.id}`} className="min-w-0 flex-1 py-1">
                      <p className="flex items-center gap-2 break-words font-semibold leading-tight">
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
                      {account.active ? "Actif" : "Inactif"}
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
                        Euro : {formatRate(account.fonds_euros_pct || 0, 1)} / Investi : {formatRate(account.fonds_investis_pct || 0, 1)}
                      </Badge>
                    )}
                  </div>
                  <div className="mt-3 flex items-center gap-2">
                    <Button asChild className="h-10 flex-1 bg-slate-900 text-white hover:bg-slate-800">
                      <Link to={`/accounts/${account.id}`}>Voir détails <ArrowRight className="ml-2 h-4 w-4" /></Link>
                    </Button>
                    <Button
                      variant="outline"
                      className="h-10"
                      onClick={() => openEdit(account)}
                    >
                      Modifier
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      aria-label="Archiver" title="Archiver"
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
                      Nom
                      {sortField === "name" && (sortOrder === "asc" ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />)}
                    </div>
                  </TableHead>
                  <TableHead className="cursor-pointer hover:bg-slate-50 transition-colors" onClick={() => handleSort("institution")}>
                    <div className="flex items-center gap-2">
                      Établissement
                      {sortField === "institution" && (sortOrder === "asc" ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />)}
                    </div>
                  </TableHead>
                  <TableHead className="cursor-pointer hover:bg-slate-50 transition-colors" onClick={() => handleSort("type")}>
                    <div className="flex items-center gap-2">
                      Type
                      {sortField === "type" && (sortOrder === "asc" ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />)}
                    </div>
                  </TableHead>
                  <TableHead className="cursor-pointer hover:bg-slate-50 transition-colors" onClick={() => handleSort("currency")}>
                    <div className="flex items-center gap-2">
                      Devise
                      {sortField === "currency" && (sortOrder === "asc" ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />)}
                    </div>
                  </TableHead>
                  <TableHead className="text-right">Solde</TableHead>
                  <TableHead>Statut</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {loading ? (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center py-8 text-muted-foreground">
                      Chargement...
                    </TableCell>
                  </TableRow>
                ) : sortedAccounts.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center py-8 text-muted-foreground">
                      Aucun compte trouvé.
                    </TableCell>
                  </TableRow>
                ) : (
                  sortedAccounts.map((account) => (
                    <TableRow key={account.id}>
                      <TableCell className="font-medium">
                        <div className="flex items-center gap-2">
                          <Button aria-label="Favori" 
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
                              Euro : {formatRate(account.fonds_euros_pct || 0, 1)} / Investi : {formatRate(account.fonds_investis_pct || 0, 1)}
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
                          {account.active ? "Actif" : "Inactif"}
                        </Badge>
                      </TableCell>
                        <TableCell className="text-right">
                          <div className="flex items-center justify-end gap-2">
                            <Button 
                              variant="outline" 
                              size="sm"
                              onClick={() => openEdit(account)}
                            >
                              Modifier
                            </Button>
                            <Button variant="ghost" size="sm" asChild>
                              <Link to={`/accounts/${account.id}`}>
                                Voir détails <ArrowRight className="ml-2 h-4 w-4" />
                              </Link>
                            </Button>
                            <Button aria-label="Archiver" title="Archiver"
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
