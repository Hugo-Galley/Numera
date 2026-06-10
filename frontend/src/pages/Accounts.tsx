import { useEffect, useState, useMemo } from "react"
import { Link } from "react-router-dom"
import {
  Plus,
  Wallet,
  TrendingUp,
  PiggyBank,
  ArrowRight,
  ArrowUp,
  ArrowDown,
  Trash2
} from "lucide-react"
import { api } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { 
  Card, 
  CardContent, 
  CardDescription, 
  CardHeader, 
  CardTitle 
} from "@/components/ui/card"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Badge } from "@/components/ui/badge"
import { toast } from "sonner"

type Account = {
  id: number
  name: string
  type: "courant" | "epargne" | "investissement"
  currency: string
  active: boolean
  asset_class?: string
  sector?: string
  geographic_zone?: string
}

export default function Accounts() {
  const [accounts, setAccounts] = useState<Account[]>([])
  const [loading, setLoading] = useState(true)
  const [isDialogOpen, setIsDialogOpen] = useState(false)
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false)
  const [editingAccount, setEditingAccount] = useState<Account | null>(null)
  
  const [newName, setNewName] = useState("")
  const [newType, setNewType] = useState<string>("courant")
  const [newCurrency, setNewCurrency] = useState<string>("EUR")
  const [newAssetClass, setNewAssetClass] = useState("")
  const [newSector, setNewSector] = useState("")
  const [newZone, setNewZone] = useState("")
  const [sortField, setSortField] = useState<"name" | "type" | "currency">("name")
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("asc")
  const [suggestions, setSuggestions] = useState<{
    asset_classes: string[],
    sectors: string[],
    geographic_zones: string[]
  }>({ asset_classes: [], sectors: [], geographic_zones: [] })

  const loadAccounts = async () => {
    setLoading(true)
    try {
      const data = await api.get<Account[]>("/accounts")
      if (data && Array.isArray(data)) {
        setAccounts(data.filter((account) => account && account.active))
      } else {
        setAccounts([])
      }
    } catch (error) {
      console.error("Error loading accounts:", error)
      toast.error("Erreur lors du chargement des comptes")
      setAccounts([])
    } finally {
      setLoading(false)
    }
  }

  const loadSuggestions = async () => {
    try {
      const data = await api.get<any>("/analytics/asset-allocation/suggestions")
      if (data) setSuggestions(data)
    } catch (error) {
      console.error("Error loading suggestions:", error)
    }
  }

  const handleSort = (field: typeof sortField) => {
    if (sortField === field) {
      setSortOrder(sortOrder === "asc" ? "desc" : "asc")
    } else {
      setSortField(field)
      setSortOrder("asc")
    }
  }

  const sortedAccounts = useMemo(() => {
    if (!accounts || !Array.isArray(accounts)) return []
    return [...accounts].sort((a, b) => {
      if (!a || !b) return 0
      let comparison = 0
      switch (sortField) {
        case "name":
          comparison = (a.name || "").localeCompare(b.name || "")
          break
        case "type":
          comparison = (a.type || "").localeCompare(b.type || "")
          break
        case "currency":
          comparison = (a.currency || "").localeCompare(b.currency || "")
          break
      }
      return sortOrder === "asc" ? comparison : -comparison
    })
  }, [accounts, sortField, sortOrder])

  useEffect(() => {
    loadAccounts()
    loadSuggestions()
  }, [])

  const handleCreateAccount = async () => {
    if (!newName) return
    try {
      await api.post("/accounts", { 
        name: newName, 
        type: newType, 
        currency: newCurrency,
        asset_class: newType === "investissement" ? newAssetClass : null,
        sector: newType === "investissement" ? newSector : null,
        geographic_zone: newType === "investissement" ? newZone : null
      })
      toast.success("Compte créé avec succès")
      setIsDialogOpen(false)
      setNewName("")
      setNewCurrency("EUR")
      setNewAssetClass("")
      setNewSector("")
      setNewZone("")
      loadAccounts()
    } catch (error) {
      toast.error("Erreur lors de la création du compte")
    }
  }

  const handleUpdateAccount = async () => {
    if (!editingAccount) return
    try {
      await api.patch(`/accounts/${editingAccount.id}`, { 
        name: editingAccount.name, 
        type: editingAccount.type, 
        currency: editingAccount.currency,
        asset_class: editingAccount.type === "investissement" ? editingAccount.asset_class : null,
        sector: editingAccount.type === "investissement" ? editingAccount.sector : null,
        geographic_zone: editingAccount.type === "investissement" ? editingAccount.geographic_zone : null
      })
      toast.success("Compte mis à jour")
      setIsEditDialogOpen(false)
      setEditingAccount(null)
      loadAccounts()
    } catch (error) {
      toast.error("Erreur lors de la mise à jour")
    }
  }

  const handleDeleteAccount = async (accountId: number) => {
    try {
      await api.delete(`/accounts/${accountId}`)
      toast.success("Compte supprimé")
      loadAccounts()
    } catch (error) {
      toast.error("Erreur lors de la suppression du compte")
    }
  }

  const getTypeIcon = (type: string) => {
    switch (type) {
      case "courant": return <Wallet className="h-4 w-4" />
      case "epargne": return <PiggyBank className="h-4 w-4" />
      case "investissement": return <TrendingUp className="h-4 w-4" />
      default: return <Wallet className="h-4 w-4" />
    }
  }

  const CURRENCIES = ["EUR", "USD", "GBP", "CHF", "JPY", "CAD", "AUD"]

  return (
    <div className="space-y-8">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Comptes</h1>
          <p className="text-muted-foreground">Gérez vos différents comptes bancaires et d'investissement.</p>
        </div>
        <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
          <DialogTrigger asChild>
            <Button className="bg-slate-900 text-white hover:bg-slate-800 w-full sm:w-auto">
              <Plus className="mr-2 h-4 w-4" /> Ajouter un compte
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Nouveau compte</DialogTitle>
              <DialogDescription>
                Ajoutez un nouveau compte pour suivre vos finances.
              </DialogDescription>
            </DialogHeader>
            <div className="grid gap-4 py-4">
              <div className="grid gap-2">
                <Label htmlFor="name">Nom du compte</Label>
                <Input 
                  id="name" 
                  placeholder="Ex: Compte Courant Boursorama" 
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="type">Type de compte</Label>
                <Select value={newType} onValueChange={setNewType}>
                  <SelectTrigger>
                    <SelectValue placeholder="Sélectionnez un type" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="courant">Compte Courant</SelectItem>
                    <SelectItem value="epargne">Épargne</SelectItem>
                    <SelectItem value="investissement">Investissement</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="grid gap-2">
                <Label htmlFor="currency">Devise</Label>
                <Select value={newCurrency} onValueChange={setNewCurrency}>
                  <SelectTrigger>
                    <SelectValue placeholder="EUR" />
                  </SelectTrigger>
                  <SelectContent>
                    {CURRENCIES.map(c => (
                      <SelectItem key={c} value={c}>{c}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {newType === "investissement" && (
                <div className="grid gap-4 pt-2 border-t mt-2">
                  <h3 className="text-sm font-bold uppercase tracking-wider text-slate-500">Asset Allocation</h3>
                  <div className="grid gap-2">
                    <Label htmlFor="asset_class">Classe d'actif</Label>
                    <Input 
                      id="asset_class" 
                      placeholder="Ex: Actions, Crypto..." 
                      value={newAssetClass} 
                      onChange={(e) => setNewAssetClass(e.target.value)} 
                      list="classes-list"
                    />
                    <datalist id="classes-list">
                      {suggestions.asset_classes.map(c => <option key={c} value={c} />)}
                    </datalist>
                  </div>
                  <div className="grid gap-2">
                    <Label htmlFor="sector">Secteur</Label>
                    <Input 
                      id="sector" 
                      placeholder="Ex: Tech, Santé..." 
                      value={newSector} 
                      onChange={(e) => setNewSector(e.target.value)} 
                      list="sectors-list"
                    />
                    <datalist id="sectors-list">
                      {suggestions.sectors.map(s => <option key={s} value={s} />)}
                    </datalist>
                  </div>
                  <div className="grid gap-2">
                    <Label htmlFor="zone">Zone Géographique</Label>
                    <Input 
                      id="zone" 
                      placeholder="Ex: USA, Europe..." 
                      value={newZone} 
                      onChange={(e) => setNewZone(e.target.value)} 
                      list="zones-list"
                    />
                    <datalist id="zones-list">
                      {suggestions.geographic_zones.map(z => <option key={z} value={z} />)}
                    </datalist>
                  </div>
                </div>
              )}
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setIsDialogOpen(false)}>Annuler</Button>
              <Button onClick={handleCreateAccount} className="bg-slate-900 text-white">Créer</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {/* Edit Dialog */}
      <Dialog open={isEditDialogOpen} onOpenChange={setIsEditDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Modifier le compte</DialogTitle>
            <DialogDescription>
              Mettez à jour les informations du compte.
            </DialogDescription>
          </DialogHeader>
          {editingAccount && (
            <div className="grid gap-4 py-4">
              <div className="grid gap-2">
                <Label htmlFor="edit-name">Nom du compte</Label>
                <Input 
                  id="edit-name" 
                  value={editingAccount.name}
                  onChange={(e) => setEditingAccount({...editingAccount, name: e.target.value})}
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="edit-type">Type de compte</Label>
                <Select 
                  value={editingAccount.type} 
                  onValueChange={(v) => setEditingAccount({...editingAccount, type: v as any})}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="courant">Compte Courant</SelectItem>
                    <SelectItem value="epargne">Épargne</SelectItem>
                    <SelectItem value="investissement">Investissement</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="grid gap-2">
                <Label htmlFor="edit-currency">Devise</Label>
                <Select 
                  value={editingAccount.currency} 
                  onValueChange={(v) => setEditingAccount({...editingAccount, currency: v})}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {CURRENCIES.map(c => (
                      <SelectItem key={c} value={c}>{c}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {editingAccount.type === "investissement" && (
                <div className="grid gap-4 pt-2 border-t mt-2">
                  <h3 className="text-sm font-bold uppercase tracking-wider text-slate-500">Asset Allocation</h3>
                  <div className="grid gap-2">
                    <Label htmlFor="edit-asset_class">Classe d'actif</Label>
                    <Input 
                      id="edit-asset_class" 
                      value={editingAccount.asset_class || ""} 
                      onChange={(e) => setEditingAccount({...editingAccount, asset_class: e.target.value})} 
                      list="edit-classes-list"
                    />
                    <datalist id="edit-classes-list">
                      {suggestions.asset_classes.map(c => <option key={c} value={c} />)}
                    </datalist>
                  </div>
                  <div className="grid gap-2">
                    <Label htmlFor="edit-sector">Secteur</Label>
                    <Input 
                      id="edit-sector" 
                      value={editingAccount.sector || ""} 
                      onChange={(e) => setEditingAccount({...editingAccount, sector: e.target.value})} 
                      list="edit-sectors-list"
                    />
                    <datalist id="edit-sectors-list">
                      {suggestions.sectors.map(s => <option key={s} value={s} />)}
                    </datalist>
                  </div>
                  <div className="grid gap-2">
                    <Label htmlFor="edit-zone">Zone Géographique</Label>
                    <Input 
                      id="edit-zone" 
                      value={editingAccount.geographic_zone || ""} 
                      onChange={(e) => setEditingAccount({...editingAccount, geographic_zone: e.target.value})} 
                      list="edit-zones-list"
                    />
                    <datalist id="edit-zones-list">
                      {suggestions.geographic_zones.map(z => <option key={z} value={z} />)}
                    </datalist>
                  </div>
                </div>
              )}
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsEditDialogOpen(false)}>Annuler</Button>
            <Button onClick={handleUpdateAccount} className="bg-slate-900 text-white">Enregistrer</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Card>
        <CardHeader>
          <CardTitle>Liste des comptes</CardTitle>
          <CardDescription>Tous vos comptes actifs.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="rounded-md border overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="cursor-pointer hover:bg-slate-50 transition-colors" onClick={() => handleSort("name")}>
                    <div className="flex items-center gap-2">
                      Nom
                      {sortField === "name" && (sortOrder === "asc" ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />)}
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
                  <TableHead>Statut</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {loading ? (
                  <TableRow>
                    <TableCell colSpan={5} className="text-center py-8 text-muted-foreground">
                      Chargement...
                    </TableCell>
                  </TableRow>
                ) : sortedAccounts.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={5} className="text-center py-8 text-muted-foreground">
                      Aucun compte trouvé.
                    </TableCell>
                  </TableRow>
                ) : (
                  sortedAccounts.map((account) => (
                    <TableRow key={account.id}>
                      <TableCell className="font-medium">{account.name}</TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          {getTypeIcon(account.type)}
                          <span className="capitalize">{account.type}</span>
                        </div>
                      </TableCell>
                      <TableCell>{account.currency}</TableCell>
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
                              onClick={() => {
                                setEditingAccount(account)
                                setIsEditDialogOpen(true)
                              }}
                            >
                              Modifier
                            </Button>
                            <Button variant="ghost" size="sm" asChild>
                              <Link to={`/accounts/${account.id}`}>
                                Voir détails <ArrowRight className="ml-2 h-4 w-4" />
                              </Link>
                            </Button>
                            <Button
                              variant="ghost"
                              size="icon"
                              className="text-rose-600 hover:text-rose-700"
                              onClick={() => handleDeleteAccount(account.id)}
                            >
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
    </div>
  )
}
