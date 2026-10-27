import { useEffect, useState } from "react"
import { ArrowRight, Download } from "lucide-react"
import { toast } from "sonner"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Checkbox } from "@/components/ui/checkbox"
import { Label } from "@/components/ui/label"
import { api } from "@/lib/api"

type Account = {
  id: number
  name: string
  type: string
  active: boolean
}

export function ExportCard() {
  const [accounts, setAccounts] = useState<Account[]>([])
  const [selectedAccounts, setSelectedAccounts] = useState<number[]>([])

  const loadAccounts = async () => {
    try {
      const data = await api.get<Account[]>("/accounts")
      const activeAccounts = data.filter((a) => a.active)
      setAccounts(activeAccounts)
      // Par défaut, on sélectionne tout
      setSelectedAccounts(activeAccounts.map(a => a.id))
    } catch (error) {
      console.error("Erreur chargement comptes", error)
      toast.error("Impossible de charger les comptes")
    }
  }

  useEffect(() => {
    loadAccounts()
  }, [])

  const handleExport = async () => {
    // Téléchargement authentifié (le JWT ne peut pas passer par window.location)
    const params = new URLSearchParams()
    if (selectedAccounts.length > 0) {
      params.append("account_ids", selectedAccounts.join(","))
    }
    try {
      const blob = await api.download(`/export/transactions.csv?${params.toString()}`)
      const url = URL.createObjectURL(blob)
      const a = document.createElement("a")
      a.href = url
      a.download = "transactions_export.csv"
      a.click()
      URL.revokeObjectURL(url)
    } catch (error: any) {
      toast.error(error?.message || "Erreur lors de l'export")
    }
  }

  return (
    <Card className="shadow-sm border-slate-100 overflow-hidden">
      <CardHeader className="bg-slate-50/50 border-b">
        <CardTitle className="text-lg">Données et Export</CardTitle>
        <CardDescription>Téléchargez vos données pour les utiliser ailleurs.</CardDescription>
      </CardHeader>
      <CardContent className="p-4 sm:p-6 space-y-6">
        <div className="space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <Label className="text-sm font-bold text-slate-700 uppercase tracking-wider">Comptes à inclure</Label>
            <div className="flex gap-2">
              <Button 
                variant="ghost" 
                size="sm" 
                className="h-10 sm:h-7 text-[10px] uppercase font-bold px-3 sm:px-2"
                onClick={() => setSelectedAccounts(accounts.map(a => a.id))}
              >
                Tout sélectionner
              </Button>
              <Button 
                variant="ghost" 
                size="sm" 
                className="h-10 sm:h-7 text-[10px] uppercase font-bold px-3 sm:px-2"
                onClick={() => setSelectedAccounts([])}
              >
                Tout désélectionner
              </Button>
            </div>
          </div>
          
          <div className="grid gap-3 grid-cols-1 sm:grid-cols-2">
            {accounts.map((account) => (
              <div 
                key={account.id} 
                className="flex min-h-12 items-center space-x-3 p-3 border rounded-xl bg-white hover:bg-slate-50 transition-colors"
              >
                <Checkbox 
                  id={`account-${account.id}`} 
                  checked={selectedAccounts.includes(account.id)}
                  onCheckedChange={(checked) => {
                    if (checked) {
                      setSelectedAccounts([...selectedAccounts, account.id])
                    } else {
                      setSelectedAccounts(selectedAccounts.filter(id => id !== account.id))
                    }
                  }}
                />
                <label
                  htmlFor={`account-${account.id}`}
                  className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 cursor-pointer flex-1 truncate"
                >
                  {account.name}
                </label>
              </div>
            ))}
          </div>
        </div>

        <div className="pt-4 border-t">
          <Button 
            onClick={handleExport}
            disabled={selectedAccounts.length === 0}
            className="w-full bg-slate-900 text-white hover:bg-slate-800 h-auto sm:h-14 py-4 sm:py-0 rounded-2xl shadow-lg flex items-center justify-between px-6 group transition-all"
          >
            <div className="flex items-center gap-4">
              <div className="bg-slate-800 p-2 rounded-lg group-hover:bg-slate-700 transition-colors hidden sm:block">
                <Download className="h-5 w-5" />
              </div>
              <div className="text-left">
                <p className="font-bold">Exporter en CSV</p>
                <p className="text-[10px] opacity-70 uppercase tracking-widest">
                  {selectedAccounts.length} compte(s) sélectionné(s)
                </p>
              </div>
            </div>
            <ArrowRight className="h-5 w-5 group-hover:translate-x-1 transition-transform" />
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
