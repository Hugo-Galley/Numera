import { useEffect, useState } from "react"
import {
  ArrowRightLeft,
  Link,
  Unlink,
  CheckCircle2,
  AlertCircle,
  Calendar,
  Wallet,
  ArrowRight
} from "lucide-react"
import {
  Card,
  CardContent,
} from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { api } from "@/lib/api"
import { Badge } from "@/components/ui/badge"
import { toast } from "sonner"
import { format } from "date-fns"
import { fr } from "date-fns/locale"

export function TransfersTab() {
  const [potentials, setPotentials] = useState<any[]>([])
  const [linked, setLinked] = useState<any[]>([])
  const [accounts, setAccounts] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadData()
  }, [])

  async function loadData() {
    setLoading(true)
    try {
      const [p, l, accs] = await Promise.all([
        api.get<any[]>("/transactions/potential-transfers"),
        api.get<any[]>("/transactions?is_transfer=true&limit=50"),
        api.get<any[]>("/accounts")
      ])
      setPotentials(p)
      setLinked(l)
      setAccounts(accs)
    } catch (error) {
      console.error("Failed to load transfers", error)
      toast.error("Erreur lors du chargement des transferts")
    } finally {
      setLoading(false)
    }
  }

  async function handleLink(sortieId: number, entreeId: number, type: string = "regular") {
    try {
      await api.post(`/transactions/${sortieId}/link/${entreeId}?type=${type}`, {})
      toast.success("Transactions liées avec succès")
      loadData()
    } catch (error) {
      toast.error("Échec de la liaison")
    }
  }

  async function handleIgnore(id: number) {
    try {
      await api.post(`/transactions/${id}/ignore`, {})
      toast.success("Suggestion ignorée")
      loadData()
    } catch (error) {
      toast.error("Échec de l'action")
    }
  }

  async function handleUnlink(id: number) {
    if (!confirm("Voulez-vous délier ces transactions ?")) return
    try {
      await api.post(`/transactions/${id}/unlink`, {})
      toast.success("Transactions déliées")
      loadData()
    } catch (error) {
      toast.error("Échec de l'action")
    }
  }

  const getAccountName = (id: number) => accounts.find(a => a.id === id)?.name || "Compte inconnu"

  const formatCurrency = (amount: number, currency: string = "EUR") => {
    return new Intl.NumberFormat('fr-FR', { style: 'currency', currency }).format(amount)
  }

  if (loading) return <div className="p-8 text-center text-slate-500">Chargement...</div>

  return (
    <div className="space-y-8">
      {/* Potential Transfers Section */}
      <section className="space-y-4">
        <div>
          <h3 className="text-lg font-bold text-slate-900 flex items-center gap-2">
            <ArrowRightLeft className="h-5 w-5 text-indigo-500" />
            Transferts potentiels détectés
          </h3>
          <p className="text-sm text-slate-500 mt-1">
            Ces transactions ressemblent à des mouvements internes entre vos comptes. Liez-les pour les exclure de vos dépenses réelles.
          </p>
        </div>

        <div className="grid gap-4">
          {potentials.map((pair, idx) => (
            <Card key={idx} className="border-slate-100 shadow-sm overflow-hidden hover:border-indigo-200 transition-colors">
              <CardContent className="p-4 flex items-center justify-between">
                <div className="flex items-center gap-6 flex-1">
                  {/* Sortie Side */}
                  <div className="flex-1 space-y-1">
                    <div className="flex items-center gap-2">
                      <Wallet className="h-3 w-3 text-slate-400" />
                      <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">{getAccountName(pair.sortie.account_id)}</span>
                    </div>
                    <p className="font-bold text-slate-900">{pair.sortie.merchant}</p>
                    <div className="flex items-center gap-2 text-xs text-slate-400">
                      <Calendar className="h-3 w-3" />
                      {format(new Date(pair.sortie.date), 'dd MMMM yyyy', { locale: fr })}
                      <span className="font-medium text-red-500">-{formatCurrency(pair.sortie.amount, pair.sortie.currency)}</span>
                    </div>
                  </div>

                  <div className="flex flex-col items-center gap-1">
                     <ArrowRight className="h-5 w-5 text-indigo-400" />
                     {pair.confidence === 'high' ? (
                       <Badge variant="outline" className="text-[10px] px-1 py-0 bg-green-50 text-green-700 border-green-100">Confiance Haute</Badge>
                     ) : (
                       <Badge variant="outline" className="text-[10px] px-1 py-0 bg-amber-50 text-amber-700 border-amber-100">Moyenne</Badge>
                     )}
                  </div>

                  {/* Entree Side */}
                  <div className="flex-1 space-y-1 text-right">
                    <div className="flex items-center gap-2 justify-end">
                      <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">{getAccountName(pair.entree.account_id)}</span>
                      <Wallet className="h-3 w-3 text-slate-400" />
                    </div>
                    <p className="font-bold text-slate-900">{pair.entree.merchant}</p>
                    <div className="flex items-center gap-2 text-xs text-slate-400 justify-end">
                      <span className="font-medium text-emerald-500">+{formatCurrency(pair.entree.amount, pair.entree.currency)}</span>
                      {format(new Date(pair.entree.date), 'dd MMMM yyyy', { locale: fr })}
                      <Calendar className="h-3 w-3" />
                    </div>
                  </div>
                </div>

                <div className="ml-8 flex flex-col gap-2">
                  <Button size="sm" className="gap-2 bg-indigo-600 hover:bg-indigo-700" onClick={() => handleLink(pair.sortie.id, pair.entree.id, pair.type)}>
                    <Link className="h-4 w-4" />
                    Lier
                  </Button>
                  <Button variant="ghost" size="sm" className="text-slate-400 hover:text-slate-600" onClick={() => handleIgnore(pair.sortie.id)}>
                    Ignorer
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}

          {potentials.length === 0 && (
            <div className="p-12 text-center text-slate-400 italic bg-slate-50 rounded-xl border border-dashed border-slate-200">
              Aucun nouveau transfert potentiel détecté.
            </div>
          )}
        </div>
      </section>

      {/* Already Linked Section */}
      <section className="space-y-4">
        <div>
          <h3 className="text-lg font-bold text-slate-900 flex items-center gap-2">
            <CheckCircle2 className="h-5 w-5 text-emerald-500" />
            Transferts liés
          </h3>
          <p className="text-sm text-slate-500 mt-1">
            Derniers transferts identifiés et rapprochés.
          </p>
        </div>

        <Card className="border-slate-100 shadow-sm overflow-hidden">
          <CardContent className="p-0">
             <div className="divide-y divide-slate-100">
               {linked.filter(tx => tx.type === 'Sortie' && (tx.linked_transaction_id || tx.linked_investment_transaction_id)).map((tx) => (
                 <div key={tx.id} className="p-4 flex items-center justify-between hover:bg-slate-50 transition-colors">
                    <div className="flex items-center gap-4">
                       <div className="h-10 w-10 bg-emerald-50 rounded-xl flex items-center justify-center text-emerald-600">
                         <ArrowRightLeft className="h-5 w-5" />
                       </div>
                       <div>
                         <p className="font-bold text-slate-900">{tx.merchant}</p>
                         <div className="flex items-center gap-2 mt-0.5">
                           <span className="text-xs text-slate-500">{getAccountName(tx.account_id)}</span>
                           <ArrowRight className="h-3 w-3 text-slate-300" />
                           <span className="text-xs text-slate-500">
                             {tx.linked_transaction_id ? getAccountName(tx.linked_transaction_id) : "Investissement"}
                           </span>
                           <span className="text-xs text-slate-300 mx-1">•</span>
                           <span className="text-xs text-slate-400">{format(new Date(tx.date), 'dd/MM/yyyy')}</span>
                         </div>
                       </div>
                    </div>
                    <div className="flex items-center gap-4">
                       <span className="font-bold text-slate-700">{formatCurrency(tx.amount, tx.currency)}</span>
                       <Button variant="ghost" size="sm" className="text-slate-400 hover:text-red-600 hover:bg-red-50 h-8 w-8 p-0" onClick={() => handleUnlink(tx.id)}>
                         <Unlink className="h-4 w-4" />
                       </Button>
                    </div>
                 </div>
               ))}

               {linked.length === 0 && (
                 <div className="p-12 text-center text-slate-400 italic">
                   Aucun transfert lié pour le moment.
                 </div>
               )}
             </div>
          </CardContent>
        </Card>
      </section>

      <div className="p-4 bg-blue-50 rounded-xl border border-blue-100 flex gap-3">
         <AlertCircle className="h-5 w-5 text-blue-600 shrink-0" />
         <p className="text-xs text-blue-800 leading-relaxed">
           Les transferts liés sont automatiquement exclus des KPI de **revenus totaux** et **dépenses réelles** dans votre budget pour éviter de fausser votre taux d'épargne. Ils restent visibles dans le détail de chaque compte.
         </p>
      </div>
    </div>
  )
}
