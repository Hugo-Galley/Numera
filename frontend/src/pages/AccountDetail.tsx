import { useState, useEffect, useMemo } from "react"
import { useParams, Link } from "react-router-dom"
import { 
  ArrowLeft, 
  Plus, 
  Filter, 
  Wallet,
  History,
  BarChart3,
  TrendingUp,
  ArrowUp,
  ArrowDown,
  ArrowUpRight,
  ArrowDownRight,
  Activity,
  Calendar,
  Search,
  ChevronRight,
  Target,
  Percent,
  LineChart as LineChartIcon,
  Pencil,
  Trash2,
  Tag,
  Coffee,
  ShoppingBag,
  Utensils,
  Car,
  Home,
  Heart,
  Zap,
  Music,
  Smartphone,
  Plane,
  Gift,
  Briefcase,
  CreditCard,
  Banknote,
  Trophy,
  User,
  Film,
  Dumbbell,
  Repeat,
  Airplay,
  AlarmClock,
  Archive,
  Award,
  Backpack,
  Bath,
  Beer,
  Bell,
  Bike,
  Book,
  Box,
  Camera,
  Clapperboard,
  Cloud,
  Compass,
  Cookie,
  Cpu,
  Dice5,
  Dog,
  Droplet,
  Egg,
  Eye,
  Fan,
  Feather,
  Fish,
  Flag,
  Flashlight,
  FlaskConical,
  Flower,
  Footprints,
  Fuel,
  Gamepad2,
  GlassWater,
  Globe,
  Grape,
  Hammer,
  IceCream,
  Key,
  Laptop,
  Library,
  Lightbulb,
  Locate,
  Lock,
  Map,
  Mic,
  Monitor,
  Moon,
  Mountain,
  Mouse,
  Network,
  Newspaper,
  Nut,
  Package,
  Paintbrush,
  Palmtree,
  Paperclip,
  PawPrint,
  Phone,
  Pizza,
  Plug,
  Printer,
  Puzzle,
  Radio,
  Receipt,
  Recycle,
  Rocket,
  Route,
  Rss,
  Sailboat,
  Scissors,
  ScreenShare,
  Settings as SettingsIcon,  Shield,
  Ship,
  Shirt,
  ShowerHead,
  Skull,
  Smile,
  Snowflake,
  Speaker,
  Sprout,
  Stamp,
  Star,
  Stethoscope,
  Sun,
  Sunrise,
  Sunset,
  Tablet,
  Tent,
  Terminal,
  Thermometer,
  Ticket,
  Timer,
  Train,
  Trash,
  TreeDeciduous,
  TreePine,
  Trees,
  Tv,
  Umbrella,
  UtilityPole,
  Variable,
  Video,
  Voicemail,
  Volume2,
  Watch,
  Waves,
  Webcam,
  Weight,
  Wifi,
  Wind,
  Wine,
  Wrench,
  Check,
  X
} from "lucide-react"
import { api } from "@/lib/api"
import { COUNTRIES } from "@/lib/countries"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Label } from "@/components/ui/label"
import { 
  Select, 
  SelectContent, 
  SelectItem, 
  SelectTrigger, 
  SelectValue 
} from "@/components/ui/select"
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
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Badge } from "@/components/ui/badge"
import { Checkbox } from "@/components/ui/checkbox"
import { toast } from "sonner"
import { 
  format, 
  startOfMonth, 
  endOfMonth, 
  subMonths,
  startOfYear,
  endOfYear
} from "date-fns"
import { fr } from "date-fns/locale"
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  LineChart,
  Line
} from "recharts"
import { Separator } from "@/components/ui/separator"
import { Input } from "@/components/ui/input"

type Account = {
  id: number
  name: string
  type: "courant" | "epargne" | "investissement" | "assurance_vie"
  currency: string
  fonds_euros_pct?: number
  fonds_investis_pct?: number
}

type Category = {
  id: number
  name: string
  icon?: string
  color?: string
}

type TagType = {
  id: number
  name: string
  color: string | null
}

type Transaction = {
  id: number
  date: string
  type: string
  merchant: string
  merchant_id: number | null
  merchant_obj?: {
    id: number
    name: string
    color: string | null
  } | null
  amount: number
  currency: string
  original_amount: number
  running_balance: number
  category_id: number | null
  category: Category | null
  tags: TagType[]
  note: string | null
  is_recurring: boolean
  custom_icon: string | null
  custom_color: string | null
}

const ICON_MAP: Record<string, any> = {
  Coffee, ShoppingBag, Utensils, Car, Home, Heart, Zap, Music, Smartphone, Plane, Gift, 
  Briefcase, CreditCard, Wallet, Banknote, 
  Trophy, Activity, User, Film, Dumbbell, Tag,
  Airplay, AlarmClock, Archive, Award, Backpack, Bath, Beer, Bell, Bike, Book, Box, Camera,
  Clapperboard, Cloud, Compass, Cookie, Cpu, Dice5, Dog, Droplet, Egg, Eye, Fan, Feather,
  Fish, Flag, Flashlight, FlaskConical, Flower, Footprints, Fuel, Gamepad2, GlassWater,
  Globe, Grape, Hammer, IceCream, Key, Laptop, Library, Lightbulb, Locate, Lock,
  Map, Mic, Monitor, Moon, Mountain, Mouse, Network, Newspaper, Nut, Package, Paintbrush,
  Palmtree, Paperclip, PawPrint, Phone, Pizza, Plug, Printer, Puzzle, Radio, Receipt,
  Recycle, Rocket, Route, Rss, Sailboat, Scissors, ScreenShare, Search, Settings: SettingsIcon,
  Shield, Ship, Shirt, ShowerHead, Skull, Smile, Snowflake, Speaker, Sprout, Stamp, Star,
  Stethoscope, Sun, Sunrise, Sunset, Tablet, Target, Tent, Terminal, Thermometer, Ticket,
  Timer, Train, Trash, TreeDeciduous, TreePine, Trees, Tv, Umbrella, UtilityPole, Variable,
  Video, Voicemail, Volume2, Watch, Waves, Webcam, Weight, Wifi, Wind, Wine, Wrench
}

const IconComponent = ({ name, className }: { name?: string, className?: string }) => {
  if (name && (name.startsWith("M") || name.startsWith("<svg") || name.includes("<path"))) {
    return (
      <svg 
        viewBox="0 0 24 24" 
        className={className} 
        fill="none" 
        stroke="currentColor" 
        strokeWidth="2" 
        strokeLinecap="round" 
        strokeLinejoin="round"
      >
        {name.startsWith("<svg") ? (
          <g dangerouslySetInnerHTML={{ __html: name.replace(/<svg[^>]*>|<\/svg>/g, '') }} />
        ) : name.includes("<path") ? (
          <g dangerouslySetInnerHTML={{ __html: name }} />
        ) : (
          <path d={name} />
        )}
      </svg>
    )
  }
  const Icon = ICON_MAP[name || "Tag"] || Tag
  return <Icon className={className} />
}

const getMerchantIcon = (merchantName: string) => {
  const name = merchantName.toLowerCase();
  if (name.includes("spotify") || name.includes("music")) return "Music";
  if (name.includes("netflix") || name.includes("disney") || name.includes("canal") || name.includes("prime") || name.includes("cinema") || name.includes("ugc") || name.includes("cgr")) return "Film";
  if (name.includes("fit") || name.includes("gym") || name.includes("sport") || name.includes("neoness") || name.includes("crossfit")) return "Dumbbell";
  if (name.includes("free") || name.includes("orange") || name.includes("sfr") || name.includes("bouygues") || name.includes("sosh")) return "Smartphone";
  if (name.includes("navigo") || name.includes("sncf") || name.includes("uber") || name.includes("bolt")) return "Car";
  if (name.includes("apple") || name.includes("icloud") || name.includes("amazon") || name.includes("google")) return "Zap";
  if (name.includes("banque") || name.includes("boursorama") || name.includes("boursobank") || name.includes("credit") || name.includes("lcl") || name.includes("sg") || name.includes("n26") || name.includes("revolut")) return "Banknote";
  return "Briefcase";
}

export default function AccountDetail() {
  const { id } = useParams<{ id: string }>()
  
  // -- Data State --
  const [account, setAccount] = useState<Account | null>(null)
  const [transactions, setTransactions] = useState<Transaction[]>([])
  const [knownMerchants, setKnownMerchants] = useState<string[]>([])
  const [timeseries, setTimeseries] = useState<any>(null)
  const [investmentData, setInvestmentData] = useState<any>(null)
  const [perfHistory, setPerfHistory] = useState<any[]>([])
  const [categories, setCategories] = useState<Category[]>([])
  const [availableTags, setAvailableTags] = useState<TagType[]>([])
  const [tagTotals, setTagTotals] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState("")
  const [dateStart, setDateStart] = useState("")
  const [dateEnd, setDateEnd] = useState("")
  const [sortField, setSortField] = useState<"date" | "merchant" | "amount" | "category" | "type" | "running_balance">("date")
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc")
  const [invSortField, setInvSortField] = useState<"date" | "type" | "amount">("date")
  const [invSortOrder, setInvSortOrder] = useState<"asc" | "desc">("desc")
  const [snapSortField, setSnapSortField] = useState<"date" | "current_value">("date")
  const [snapSortOrder, setSnapSortOrder] = useState<"asc" | "desc">("desc")

  const [filterType, setFilterType] = useState<string>("all")
  const [filterCategory, setFilterCategory] = useState<string>("all")
  const [filterMerchant, setFilterMerchant] = useState<string>("all")
  const [filterTags, setFilterTags] = useState<number[]>([])

  const [selectedIds, setSelectedIds] = useState<number[]>([])
  const [isBulkEditDialogOpen, setIsBulkEditDialogOpen] = useState(false)
  const [bulkCategory, setBulkCategory] = useState<string>("keep")
  const [bulkRecurring, setBulkRecurring] = useState<string>("keep")
  const [bulkTagIds, setBulkTagIds] = useState<number[]>([])
  const [bulkTagAction, setBulkTagAction] = useState<"keep" | "replace">("keep")

  const handleSort = (field: typeof sortField) => {
    if (sortField === field) {
      setSortOrder(sortOrder === "asc" ? "desc" : "asc")
    } else {
      setSortField(field)
      setSortOrder("desc")
    }
  }

  const handleInvSort = (field: typeof invSortField) => {
    if (invSortField === field) {
      setInvSortOrder(invSortOrder === "asc" ? "desc" : "asc")
    } else {
      setInvSortField(field)
      setInvSortOrder("desc")
    }
  }

  const sortedInvestmentTransactions = useMemo(() => {
    return [...(investmentData?.transactions || [])].sort((a, b) => {
      let comparison = 0
      switch (invSortField) {
        case "date":
          comparison = new Date(a.date).getTime() - new Date(b.date).getTime()
          break
        case "type":
          comparison = a.type.localeCompare(b.type)
          break
        case "amount":
          comparison = a.amount - b.amount
          break
      }
      
      if (comparison === 0) {
        comparison = a.id - b.id
      }
      
      return invSortOrder === "asc" ? comparison : -comparison
    })
  }, [investmentData?.transactions, invSortField, invSortOrder])

  const handleSnapSort = (field: typeof snapSortField) => {
    if (snapSortField === field) {
      setSnapSortOrder(snapSortOrder === "asc" ? "desc" : "asc")
    } else {
      setSnapSortField(field)
      setSnapSortOrder("desc")
    }
  }

  const sortedSnapshots = useMemo(() => {
    return [...(investmentData?.value_series || [])].sort((a, b) => {
      let comparison = 0
      switch (snapSortField) {
        case "date":
          comparison = new Date(a.date).getTime() - new Date(b.date).getTime()
          break
        case "current_value":
          comparison = a.current_value - b.current_value
          break
      }
      
      if (comparison === 0) {
        comparison = a.id - b.id
      }
      
      return snapSortOrder === "asc" ? comparison : -comparison
    })
  }, [investmentData?.value_series, snapSortField, snapSortOrder])

  const handleQuickFilter = (value: string) => {
    const now = new Date()
    switch (value) {
      case "all":
        setDateStart("")
        setDateEnd("")
        break
      case "current-month":
        setDateStart(format(startOfMonth(now), "yyyy-MM-dd"))
        setDateEnd(format(endOfMonth(now), "yyyy-MM-dd"))
        break
      case "last-3-months":
        setDateStart(format(subMonths(now, 3), "yyyy-MM-dd"))
        setDateEnd(format(now, "yyyy-MM-dd"))
        break
      case "current-year":
        setDateStart(format(startOfYear(now), "yyyy-MM-dd"))
        setDateEnd(format(endOfYear(now), "yyyy-MM-dd"))
        break
    }
  }

  // -- Transaction Form State --
  const [txOpen, setTxOpen] = useState(false)
  const [editTxId, setEditTxId] = useState<number | null>(null)
  const [txDate, setTxDate] = useState(() => new Date().toISOString().slice(0, 16))
  const [txType, setTxType] = useState("Sortie")
  const [txMerchant, setTxMerchant] = useState("")
  const [txAmount, setTxAmount] = useState("")
  const [txCurrency, setTxCurrency] = useState("EUR")
  const [txCategoryId, setTxCategoryId] = useState<string>("none")
  const [txTagIds, setTxTagIds] = useState<number[]>([])
  const [txNote, setTxNote] = useState("")
  const [txIsRecurring, setTxIsRecurring] = useState(false)
  const [txCustomIcon, setTxCustomIcon] = useState("")
  const [txCustomColor, setTxCustomColor] = useState("#0f172a")

  // -- Snapshot Form State --
  const [snapOpen, setSnapOpen] = useState(false)
  const [editSnapId, setEditSnapId] = useState<number | null>(null)
  const [snapDate, setSnapDate] = useState(() => new Date().toISOString().slice(0, 10))
  const [snapValue, setSnapValue] = useState("")
  const [snapNote, setSnapNote] = useState("")

  // -- Investment Flux Form State --
  const [invTxOpen, setInvTxOpen] = useState(false)
  const [editInvTxId, setEditInvTxId] = useState<number | null>(null)
  const [invTxDate, setInvTxDate] = useState(() => new Date().toISOString().slice(0, 16))
  const [invTxType, setInvTxType] = useState<"versement" | "retrait" | "dividende">("versement")
  const [invTxAmount, setInvTxAmount] = useState("")
  const [invTxCurrency, setInvTxCurrency] = useState("EUR")
  const [invTxNote, setInvTxNote] = useState("")
  const [invTxAssetClass, setInvTxAssetClass] = useState("")
  const [invTxSector, setInvTxSector] = useState("")
  const [invTxZone, setInvTxZone] = useState("")
  const [suggestions, setSuggestions] = useState<{
    asset_classes: string[],
    sectors: string[],
    geographic_zones: string[]
  }>({ asset_classes: [], sectors: [], geographic_zones: [] })

  // -- Zero Point Form State --
  const [zeroOpen, setZeroOpen] = useState(false)
  const [zeroDate, setZeroDate] = useState(() => new Date().toISOString().slice(0, 10))
  const [zeroValue, setZeroValue] = useState("")
  const [zeroNote, setZeroNote] = useState("")

  const loadData = async () => {
    if (!id) return
    setLoading(true)
    try {
      const [accData, merchantsData, suggestionsData] = await Promise.all([
        api.get<Account>(`/accounts/${id}`),
        api.get<string[]>("/transactions/merchants"),
        api.get<any>("/analytics/asset-allocation/suggestions")
      ])
      setAccount(accData)
      setKnownMerchants(merchantsData)
      if (suggestionsData) setSuggestions(suggestionsData)
      setTxCurrency(accData.currency)
      setInvTxCurrency(accData.currency)

      if (accData.type === "investissement" || accData.type === "assurance_vie") {
        const [invData, perfData] = await Promise.all([
          api.get<any>(`/analytics/investments/${id}`),
          api.get<any>(`/analytics/investments/${id}/performance-history`)
        ])
        setInvestmentData(invData)
        setPerfHistory(perfData.items || [])
      } else {
        const params = new URLSearchParams()
        params.append("account_id", id!)
        if (filterType !== "all") params.append("type", filterType)
        if (filterCategory !== "all") params.append("category_id", filterCategory)
        if (filterMerchant !== "all") params.append("merchant", filterMerchant)
        if (dateStart) params.append("start_date", new Date(dateStart).toISOString())
        if (dateEnd) params.append("end_date", new Date(dateEnd).toISOString())
        if (filterTags.length > 0) {
          filterTags.forEach(tid => params.append("tag_ids", String(tid)))
        }

        const [txData, timeData, catData, tagsData, tagTotalsData] = await Promise.all([
          api.get<Transaction[]>(`/transactions?${params.toString()}`),
          api.get<any>(`/analytics/timeseries?account_id=${id}&year=${new Date().getFullYear()}`),
          api.get<Category[]>("/categories"),
          api.get<TagType[]>("/tags"),
          api.get<any[]>(`/analytics/tags?account_id=${id}${dateStart ? `&start_date=${dateStart}` : ""}${dateEnd ? `&end_date=${dateEnd}` : ""}`)
        ])
        setTransactions(txData)
        setTimeseries(timeData)
        setCategories(catData)
        setAvailableTags(tagsData)
        setTagTotals(tagTotalsData)
      }
    } catch (error) {
      toast.error("Erreur lors du chargement des données")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [id, filterType, filterCategory, filterMerchant, filterTags, dateStart, dateEnd])

  // -- Handlers (Current Account) --
  const resetTxForm = () => {
    setEditTxId(null)
    setTxDate(new Date().toISOString().slice(0, 16))
    setTxType("Sortie")
    setTxMerchant("")
    setTxAmount("")
    setTxCurrency(account?.currency || "EUR")
    setTxCategoryId("none")
    setTxTagIds([])
    setTxNote("")
    setTxIsRecurring(false)
    setTxCustomIcon("")
    setTxCustomColor("#0f172a")
  }

  const handleCreateTransaction = async () => {
    let merchant = txMerchant
    if (txType === "Solde Initial" && !merchant) {
      merchant = "Solde Initial"
    }

    if (!merchant) {
      toast.error("Veuillez saisir un commerçant ou un libellé")
      return
    }
    if (!txAmount) {
      toast.error("Veuillez saisir un montant")
      return
    }

    try {
      const payload = {
        account_id: Number(id),
        date: new Date(txDate).toISOString(),
        type: txType,
        merchant: merchant,
        category_id: txCategoryId && txCategoryId !== "none" ? Number(txCategoryId) : null,
        tag_ids: txTagIds,
        amount: Number(txAmount),
        currency: txCurrency,
        note: txNote || null,
        is_recurring: txIsRecurring,
        custom_icon: txCustomIcon || null,
        custom_color: txCustomColor || null
      }
      await api.post("/transactions", payload)
      toast.success("Transaction ajoutée")
      setTxOpen(false)
      resetTxForm()
      await loadData()
    } catch (error: any) {
      const detail = error.response?.data?.detail
      toast.error(detail || "Erreur lors de l'ajout")
    }
  }

  const handleUpdateTransaction = async () => {
    if (!editTxId) return
    
    let merchant = txMerchant
    if (txType === "Solde Initial" && !merchant) {
      merchant = "Solde Initial"
    }

    if (!merchant) {
      toast.error("Veuillez saisir un commerçant ou un libellé")
      return
    }
    if (!txAmount) {
      toast.error("Veuillez saisir un montant")
      return
    }

    try {
      const payload: any = {
        date: new Date(txDate).toISOString(),
        type: txType,
        merchant: merchant,
        category_id: txCategoryId && txCategoryId !== "none" ? Number(txCategoryId) : null,
        tag_ids: txTagIds,
        amount: Number(txAmount),
        currency: txCurrency,
        note: txNote || null,
        is_recurring: txIsRecurring,
        custom_icon: txCustomIcon || null,
        custom_color: txCustomColor || null
      }
      await api.patch(`/transactions/${editTxId}`, payload)
      toast.success("Transaction modifiée")
      setTxOpen(false)
      resetTxForm()
      await loadData()
    } catch (error: any) {
      const detail = error.response?.data?.detail
      toast.error(detail || "Erreur lors de la modification")
    }
  }

  const handleEditTransaction = (tx: Transaction) => {
    setEditTxId(tx.id)
    setTxDate(tx.date.slice(0, 16))
    setTxType(tx.type)
    setTxMerchant(tx.merchant)
    setTxAmount(String(tx.original_amount || tx.amount))
    setTxCurrency(tx.currency || account?.currency || "EUR")
    setTxCategoryId(tx.category_id ? String(tx.category_id) : "none")
    setTxTagIds(tx.tags?.map(t => t.id) || [])
    setTxNote(tx.note || "")
    setTxIsRecurring(tx.is_recurring)
    setTxCustomIcon(tx.custom_icon || "")
    setTxCustomColor(tx.custom_color || "#0f172a")
    setTxOpen(true)
  }

  const handleDeleteTransaction = async (txId: number) => {
    if (!confirm("Supprimer cette transaction ?")) return
    try {
      await api.delete(`/transactions/${txId}`)
      toast.success("Transaction supprimée")
      await loadData()
    } catch (error) {
      toast.error("Erreur lors du suppression")
    }
  }

  // -- Handlers (Investment Flux) --
  const resetInvTxForm = () => {
    setEditInvTxId(null)
    setInvTxDate(new Date().toISOString().slice(0, 16))
    setInvTxType("versement")
    setInvTxAmount("")
    setInvTxCurrency(account?.currency || "EUR")
    setInvTxNote("")
    setInvTxAssetClass("")
    setInvTxSector("")
    setInvTxZone("")
  }

  const handleCreateInvestmentTransaction = async () => {
    if (!invTxAmount) return
    try {
      const payload = {
        account_id: Number(id),
        date: new Date(invTxDate).toISOString(),
        type: invTxType,
        amount: Number(invTxAmount),
        currency: invTxCurrency,
        note: invTxNote || null,
        asset_class: invTxAssetClass || null,
        sector: invTxSector || null,
        geographic_zone: invTxZone || null
      }
      
      if (editInvTxId) {
        await api.patch(`/investment-transactions/${editInvTxId}`, payload)
        toast.success("Opération modifiée")
      } else {
        await api.post("/investment-transactions", payload)
        toast.success("Opération enregistrée")
      }
      
      setInvTxOpen(false)
      resetInvTxForm()
      await loadData()
    } catch (error) {
      toast.error("Erreur lors de l'enregistrement")
    }
  }

  const handleEditInvTransaction = (tx: any) => {
    setEditInvTxId(tx.id)
    setInvTxDate(tx.date.slice(0, 16))
    setInvTxType(tx.type)
    setInvTxAmount(String(tx.original_amount || tx.amount))
    setInvTxCurrency(tx.currency || account?.currency || "EUR")
    setInvTxNote(tx.note || "")
    setInvTxAssetClass(tx.asset_class || "")
    setInvTxSector(tx.sector || "")
    setInvTxZone(tx.geographic_zone || "")
    setInvTxOpen(true)
  }

  const handleDeleteInvTransaction = async (txId: number) => {
    if (!confirm("Supprimer ce flux ?")) return
    try {
      await api.delete(`/investment-transactions/${txId}`)
      toast.success("Flux supprimé")
      await loadData()
    } catch (error) {
      toast.error("Erreur lors de la suppression")
    }
  }

  // -- Handlers (Snapshots) --
  const resetSnapForm = () => {
    setEditSnapId(null)
    setSnapDate(new Date().toISOString().slice(0, 10))
    setSnapValue("")
    setSnapNote("")
  }

  const handleCreateSnapshot = async () => {
    if (!snapValue) return
    try {
      const payload = {
        account_id: Number(id),
        date: snapDate,
        current_value: Number(snapValue),
        note: snapNote || null,
        is_zero_point: false
      }

      if (editSnapId) {
        await api.patch(`/balance-snapshots/${editSnapId}`, payload)
        toast.success("Snapshot modifié")
      } else {
        await api.post("/balance-snapshots", payload)
        toast.success("Snapshot enregistré")
      }
      
      setSnapOpen(false)
      resetSnapForm()
      await loadData()
    } catch (error) {
      toast.error("Erreur lors de l'enregistrement")
    }
  }

  const handleEditSnapshot = (snap: any) => {
    setEditSnapId(snap.id)
    setSnapDate(snap.date.slice(0, 10))
    setSnapValue(String(snap.current_value))
    setSnapNote(snap.note || "")
    setSnapOpen(true)
  }

  const handleDeleteSnapshot = async (snapId: number) => {
    if (!confirm("Supprimer ce snapshot ?")) return
    try {
      await api.delete(`/balance-snapshots/${snapId}`)
      toast.success("Snapshot supprimé")
      await loadData()
    } catch (error) {
      toast.error("Erreur lors de la suppression")
    }
  }

  const handleBulkUpdate = async () => {
    try {
      const payload: any = { ids: selectedIds }
      if (bulkCategory !== "keep") {
        payload.category_id = bulkCategory === "none" ? null : Number(bulkCategory)
      }
      if (bulkRecurring !== "keep") {
        payload.is_recurring = bulkRecurring === "true"
      }
      if (bulkTagAction === "replace") {
        payload.tag_ids = bulkTagIds
      }

      await api.patch("/transactions/bulk", payload)
      toast.success(`${selectedIds.length} transactions mises à jour`)
      setSelectedIds([])
      setIsBulkEditDialogOpen(false)
      await loadData()
    } catch (error) {
      toast.error("Erreur lors de la mise à jour groupée")
    }
  }

  // -- Handlers (Zero Point) --
  const resetZeroForm = () => {
    setZeroDate(new Date().toISOString().slice(0, 10))
    setZeroValue("")
    setZeroNote("")
  }

  const handleSetZeroPoint = async () => {
    if (!zeroValue) return
    try {
      const payload = {
        account_id: Number(id),
        date: new Date(zeroDate).toISOString(),
        current_value: Number(zeroValue),
        note: zeroNote || null
      }
      await api.post("/balance-snapshots/set-zero-point", payload)
      toast.success("Nouveau point zéro défini")
      setZeroOpen(false)
      resetZeroForm()
      await loadData()
    } catch (error) {
      toast.error("Erreur lors de la définition du point zéro")
    }
  }

  // -- Memos --
  const formatValue = (value: number | null | undefined, currencyCode: string = "EUR") => {
    const safeValue = value || 0
    const safeCurrency = (currencyCode && currencyCode.length === 3) ? currencyCode.toUpperCase() : "EUR"
    try {
      return new Intl.NumberFormat("fr-FR", { style: "currency", currency: safeCurrency }).format(safeValue)
    } catch (e) {
      return new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR" }).format(safeValue)
    }
  }

  const formatCurrency = (value: number) => {
    return formatValue(value, account?.currency || "EUR")
  }

  const filteredTransactions = useMemo(() => {
    return transactions
      .filter(tx => {
        const txDate = new Date(tx.date)
        const merchant = tx.merchant || ""
        const type = tx.type || ""
        const note = tx.note || ""
        const categoryName = tx.category?.name || ""
        
        const matchesSearch = merchant.toLowerCase().includes(search.toLowerCase()) ||
                             type.toLowerCase().includes(search.toLowerCase()) ||
                             note.toLowerCase().includes(search.toLowerCase()) ||
                             categoryName.toLowerCase().includes(search.toLowerCase())

        let matchesDate = true
        if (dateStart) {
          const start = new Date(dateStart)
          start.setHours(0, 0, 0, 0)
          matchesDate = matchesDate && txDate >= start
        }
        if (dateEnd) {
          const end = new Date(dateEnd)
          end.setHours(23, 59, 59, 999)
          matchesDate = matchesDate && txDate <= end
        }

        return matchesSearch && matchesDate
      })
      .sort((a, b) => {
        let comparison = 0
        switch (sortField) {
          case "date":
            comparison = new Date(a.date).getTime() - new Date(b.date).getTime()
            break
          case "merchant":
            comparison = a.merchant.localeCompare(b.merchant)
            break
          case "amount":
            comparison = a.amount - b.amount
            break
          case "category":
            const getDisplayCategory = (tx: Transaction) => {
              if (tx.type === "Solde Initial") return "Solde Initial"
              if (tx.type === "Interets") return "Intérêts"
              return tx.category?.name || "Sans catégorie"
            }
            comparison = getDisplayCategory(a).localeCompare(getDisplayCategory(b))
            break
          case "type":
            comparison = a.type.localeCompare(b.type)
            break
          case "running_balance":
            comparison = a.running_balance - b.running_balance
            break
        }
        
        // Secondary sort by ID for stability
        if (comparison === 0) {
          comparison = a.id - b.id
        }
        
        return sortOrder === "asc" ? comparison : -comparison
      })
  }, [transactions, search, dateStart, dateEnd, sortField, sortOrder])

  const stats = useMemo(() => {
    const source = (search || dateStart || dateEnd) ? filteredTransactions : transactions
    if (source.length === 0) return null
    const incomes = source.filter(t => ["Entree", "Interets", "Solde Initial"].includes(t.type))
    const expenses = source.filter(t => t.type === "Sortie")
    
    return {
      totalIn: incomes.reduce((acc, t) => acc + t.amount, 0),
      totalOut: expenses.reduce((acc, t) => acc + t.amount, 0),
      count: source.length,
      avgTx: expenses.length > 0 ? expenses.reduce((acc, t) => acc + t.amount, 0) / expenses.length : 0
    }
  }, [transactions, filteredTransactions, search, dateStart, dateEnd])

  if (loading) return (
    <div className="flex items-center justify-center h-[60vh]">
      <div className="flex flex-col items-center gap-4">
        <div className="h-12 w-12 rounded-full border-4 border-slate-200 border-t-slate-900 animate-spin" />
        <p className="text-slate-500 font-medium">Chargement du compte...</p>
      </div>
    </div>
  )
  
  if (!account) return <div>Compte non trouvé</div>

  const isInvestment = account.type === "investissement" || account.type === "assurance_vie"
  const currentBalance = isInvestment 
    ? (investmentData?.totals?.current_value || 0)
    : (transactions.length > 0 ? transactions[0].running_balance : 0)

  return (
    <div className="space-y-8 pb-10">
      {/* Breadcrumbs & Header */}
      <div className="flex flex-col gap-6">
        <div className="flex flex-col gap-4">
          <div className="flex items-center gap-2 text-sm text-slate-500">
            <Link to="/accounts" className="hover:text-slate-900 transition-colors">Comptes</Link>
            <ChevronRight className="h-3 w-3" />
            <span className="text-slate-900 font-medium">{account.name}</span>
          </div>
          
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="flex items-center gap-4">
              <div className="h-14 w-14 bg-slate-900 rounded-2xl flex items-center justify-center text-white shadow-lg">
                <Wallet className="h-7 w-7" />
              </div>
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <h1 className="text-3xl font-bold tracking-tight text-slate-900">{account.name}</h1>
                  <Badge className="bg-slate-100 text-slate-600 border-none capitalize">
                    {account.type === "assurance_vie" ? "Assurance-Vie" : account.type}
                  </Badge>
                </div>
                <p className="text-slate-500">Flux financiers en {account.currency}</p>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              {!isInvestment ? (
                <Dialog open={txOpen} onOpenChange={(open) => { if (!open) { setTxOpen(false); resetTxForm(); } else { setTxOpen(true); } }}>
                  <DialogTrigger asChild>
                    <Button className="bg-slate-900 text-white hover:bg-slate-800 shadow-md">
                      <Plus className="h-4 w-4 mr-2" /> Nouvelle opération
                    </Button>
                  </DialogTrigger>
                  <DialogContent className="sm:max-w-[425px] rounded-2xl border-none shadow-2xl max-h-[90vh] overflow-y-auto">
                    <DialogHeader>
                      <DialogTitle className="text-2xl font-bold">{editTxId ? "Modifier l'opération" : "Nouvelle opération"}</DialogTitle>
                      <DialogDescription>
                        {editTxId ? "Modifiez les détails. Les soldes seront recalculés." : "Saisissez les détails de la transaction."}
                      </DialogDescription>
                    </DialogHeader>
                    <div className="grid gap-6 py-6">
                      <div className="grid grid-cols-2 gap-4">
                        <div className="grid gap-2">
                          <Label htmlFor="date" className="text-xs uppercase tracking-wider font-bold text-slate-500">Date</Label>
                          <Input id="date" type="datetime-local" value={txDate} onChange={(e) => setTxDate(e.target.value)} className="bg-slate-50 border-slate-200" />
                        </div>
                        <div className="grid gap-2">
                          <Label htmlFor="type" className="text-xs uppercase tracking-wider font-bold text-slate-500">Flux</Label>
                          <Select value={txType} onValueChange={setTxType}>
                            <SelectTrigger id="type" className="bg-slate-50 border-slate-200"><SelectValue placeholder="Type" /></SelectTrigger>
                            <SelectContent>
                              <SelectItem value="Entree">Entrée (+)</SelectItem>
                              <SelectItem value="Sortie">Sortie (-)</SelectItem>
                              <SelectItem value="Solde Initial">Solde Initial</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                      </div>
                      <div className="grid gap-2">
                        <Label htmlFor="merchant" className="text-xs uppercase tracking-wider font-bold text-slate-500">Commerçant / Libellé</Label>
                        <Input 
                          id="merchant" 
                          list="merchant-list" 
                          autoComplete="off"
                          value={txMerchant} 
                          onChange={(e) => setTxMerchant(e.target.value)} 
                          placeholder="Ex: Carrefour..." 
                          className="bg-slate-50 border-slate-200" 
                        />
                        <datalist id="merchant-list">
                          {knownMerchants.map((m, idx) => (
                            <option key={idx} value={m} />
                          ))}
                        </datalist>
                      </div>
                      <div className="grid grid-cols-2 gap-4">
                        <div className="grid gap-2">
                          <Label htmlFor="amount" className="text-xs uppercase tracking-wider font-bold text-slate-500">Montant</Label>
                          <Input id="amount" type="number" min={0.01} step="0.01" value={txAmount} onChange={(e) => setTxAmount(e.target.value)} placeholder="0.00" className="bg-slate-50 border-slate-200 font-bold" />
                        </div>
                        <div className="grid gap-2">
                          <Label htmlFor="currency" className="text-xs uppercase tracking-wider font-bold text-slate-500">Devise</Label>
                          <Select value={txCurrency} onValueChange={setTxCurrency}>
                            <SelectTrigger id="currency" className="bg-slate-50 border-slate-200"><SelectValue placeholder="Devise" /></SelectTrigger>
                            <SelectContent>
                              <SelectItem value="EUR">EUR (€)</SelectItem>
                              <SelectItem value="USD">USD ($)</SelectItem>
                              <SelectItem value="GBP">GBP (£)</SelectItem>
                              <SelectItem value="CHF">CHF (CHF)</SelectItem>
                              <SelectItem value="JPY">JPY (¥)</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                      </div>
                      <div className="grid gap-2">
                        <Label htmlFor="category" className="text-xs uppercase tracking-wider font-bold text-slate-500">Catégorie</Label>
                        <Select value={txCategoryId} onValueChange={setTxCategoryId}>
                          <SelectTrigger id="category" className="bg-slate-50 border-slate-200"><SelectValue placeholder="Choisir..." /></SelectTrigger>
                          <SelectContent>
                            <SelectItem value="none">Aucune</SelectItem>
                            {categories.map((cat) => <SelectItem key={cat.id} value={String(cat.id)}>{cat.name}</SelectItem>)}
                          </SelectContent>
                        </Select>
                      </div>

                      {availableTags.length > 0 && (
                        <div className="grid gap-2">
                          <Label className="text-xs uppercase tracking-wider font-bold text-slate-500">Tags</Label>
                          <div className="flex flex-wrap gap-2 p-3 bg-slate-50 rounded-xl border border-slate-200">
                            {availableTags.map((tag) => (
                              <div key={tag.id} className="flex items-center space-x-2">
                                <Checkbox 
                                  id={`tag-${tag.id}`} 
                                  checked={txTagIds.includes(tag.id)}
                                  onCheckedChange={(checked) => {
                                    if (checked) {
                                      setTxTagIds([...txTagIds, tag.id])
                                    } else {
                                      setTxTagIds(txTagIds.filter(tid => tid !== tag.id))
                                    }
                                  }}
                                />
                                <label
                                  htmlFor={`tag-${tag.id}`}
                                  className="text-xs font-medium leading-none cursor-pointer"
                                >
                                  <Badge 
                                    variant="outline" 
                                    className="px-2 py-0 h-5 border-none text-white font-bold text-[9px]"
                                    style={{ backgroundColor: tag.color || "#64748b" }}
                                  >
                                    {tag.name}
                                  </Badge>
                                </label>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      <div className="flex items-center space-x-2 py-2">
                        <Checkbox id="recurring" checked={txIsRecurring} onCheckedChange={(checked) => setTxIsRecurring(!!checked)} />
                        <Label htmlFor="recurring" className="text-sm font-medium leading-none cursor-pointer">Transaction récurrente</Label>
                      </div>

                      <div className="grid grid-cols-2 gap-4">
                        <div className="grid gap-2">
                          <Label htmlFor="custom_icon" className="text-xs uppercase tracking-wider font-bold text-slate-500">Icône (Lucide)</Label>
                          <Input id="custom_icon" value={txCustomIcon} onChange={(e) => setTxCustomIcon(e.target.value)} placeholder="Ex: Coffee, Zap..." className="bg-slate-50 border-slate-200" />
                        </div>
                        <div className="grid gap-2">
                          <Label htmlFor="custom_color" className="text-xs uppercase tracking-wider font-bold text-slate-500">Couleur</Label>
                          <div className="flex gap-2">
                            <Input id="custom_color" type="color" value={txCustomColor} onChange={(e) => setTxCustomColor(e.target.value)} className="w-12 p-1 h-10 bg-slate-50 border-slate-200 cursor-pointer" />
                            <Input value={txCustomColor} onChange={(e) => setTxCustomColor(e.target.value)} className="flex-1 bg-slate-50 border-slate-200" />
                          </div>
                        </div>
                      </div>
                    </div>
                    <DialogFooter><Button variant="ghost" onClick={() => { setTxOpen(false); resetTxForm(); }}>Annuler</Button><Button onClick={editTxId ? handleUpdateTransaction : handleCreateTransaction} className="bg-slate-900 text-white shadow-lg">Enregistrer</Button></DialogFooter>
                  </DialogContent>
                </Dialog>
              ) : (
                <>
                  <Dialog open={invTxOpen} onOpenChange={(open) => { if (!open) { setInvTxOpen(false); resetInvTxForm(); } else { setInvTxOpen(true); } }}>
                    <DialogTrigger asChild>
                      <Button variant="outline" size="sm">
                        <Plus className="h-4 w-4 mr-2" /> Versement / Retrait
                      </Button>
                    </DialogTrigger>
                    <DialogContent className="sm:max-w-[425px] max-h-[90vh] overflow-y-auto">
                      <DialogHeader>
                        <DialogTitle className="text-2xl font-bold">{editInvTxId ? "Modifier le flux" : "Flux d'investissement"}</DialogTitle>
                        <DialogDescription>Enregistrez un mouvement de fonds sur ce compte.</DialogDescription>
                      </DialogHeader>
                      <div className="grid gap-6 py-6">
                        <div className="grid grid-cols-2 gap-4">
                          <div className="grid gap-2">
                            <Label className="text-xs uppercase tracking-wider font-bold text-slate-500">Date</Label>
                            <Input type="datetime-local" value={invTxDate} onChange={(e) => setInvTxDate(e.target.value)} className="bg-slate-50 border-slate-200" />
                          </div>
                          <div className="grid gap-2">
                            <Label className="text-xs uppercase tracking-wider font-bold text-slate-500">Type</Label>
                            <Select value={invTxType} onValueChange={(v: any) => setInvTxType(v)}>
                              <SelectTrigger className="bg-slate-50 border-slate-200"><SelectValue /></SelectTrigger>
                              <SelectContent>
                                <SelectItem value="versement">Versement (+)</SelectItem>
                                <SelectItem value="retrait">Retrait (-)</SelectItem>
                                <SelectItem value="dividende">Dividende (Gain)</SelectItem>
                              </SelectContent>
                            </Select>
                          </div>
                        </div>
                        <div className="grid grid-cols-2 gap-4">
                          <div className="grid gap-2">
                            <Label htmlFor="ival" className="text-xs uppercase tracking-wider font-bold text-slate-500">Montant</Label>
                            <Input id="ival" type="number" step="0.01" value={invTxAmount} onChange={(e) => setInvTxAmount(e.target.value)} placeholder="0.00" className="bg-slate-50 border-slate-200 font-bold text-lg" />
                          </div>
                          <div className="grid gap-2">
                            <Label htmlFor="icurrency" className="text-xs uppercase tracking-wider font-bold text-slate-500">Devise</Label>
                            <Select value={invTxCurrency} onValueChange={setInvTxCurrency}>
                              <SelectTrigger id="icurrency" className="bg-slate-50 border-slate-200"><SelectValue placeholder="Devise" /></SelectTrigger>
                              <SelectContent>
                                <SelectItem value="EUR">EUR (€)</SelectItem>
                                <SelectItem value="USD">USD ($)</SelectItem>
                                <SelectItem value="GBP">GBP (£)</SelectItem>
                                <SelectItem value="CHF">CHF (CHF)</SelectItem>
                                <SelectItem value="JPY">JPY (¥)</SelectItem>
                              </SelectContent>
                            </Select>
                          </div>
                        </div>
                        <div className="grid gap-2">
                          <Label htmlFor="inote" className="text-xs uppercase tracking-wider font-bold text-slate-500">Note</Label>
                          <Input id="inote" value={invTxNote} onChange={(e) => setInvTxNote(e.target.value)} placeholder="Optionnel..." className="bg-slate-50 border-slate-200" />
                        </div>

                        <div className="grid gap-4 pt-2 border-t">
                          <h3 className="text-sm font-bold uppercase tracking-wider text-slate-500">Asset Allocation</h3>
                          <div className="grid grid-cols-2 gap-4">
                            <div className="grid gap-2">
                              <Label htmlFor="aclass" className="text-xs uppercase tracking-wider font-bold text-slate-500">Classe d'actif</Label>
                              <Input 
                                id="aclass" 
                                value={invTxAssetClass} 
                                onChange={(e) => setInvTxAssetClass(e.target.value)} 
                                placeholder="Ex: Actions..." 
                                className="bg-slate-50 border-slate-200" 
                                list="classes-list"
                              />
                              <datalist id="classes-list">
                                {suggestions.asset_classes.map(c => <option key={c} value={c} />)}
                              </datalist>
                            </div>
                            <div className="grid gap-2">
                              <Label htmlFor="asector" className="text-xs uppercase tracking-wider font-bold text-slate-500">Secteur</Label>
                              <Input 
                                id="asector" 
                                value={invTxSector} 
                                onChange={(e) => setInvTxSector(e.target.value)} 
                                placeholder="Ex: Tech..." 
                                className="bg-slate-50 border-slate-200" 
                                list="sectors-list"
                              />
                              <datalist id="sectors-list">
                                {suggestions.sectors.map(s => <option key={s} value={s} />)}
                              </datalist>
                            </div>
                          </div>
                          <div className="grid gap-2">
                            <Label htmlFor="azone" className="text-xs uppercase tracking-wider font-bold text-slate-500">Zone Géo / Pays</Label>
                            <Select value={invTxZone} onValueChange={setInvTxZone}>
                              <SelectTrigger className="bg-slate-50 border-slate-200">
                                <SelectValue placeholder="Sélectionner un pays..." />
                              </SelectTrigger>
                              <SelectContent>
                                {COUNTRIES.map((c) => (
                                  <SelectItem key={c.code} value={c.code}>{c.name}</SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                          </div>
                        </div>
                      </div>
                      <DialogFooter>
                        <Button variant="ghost" onClick={() => { setInvTxOpen(false); resetInvTxForm(); }}>Annuler</Button>
                        <Button onClick={handleCreateInvestmentTransaction} className="bg-slate-900 text-white shadow-lg">Confirmer</Button>
                      </DialogFooter>
                    </DialogContent>
                  </Dialog>

                  <Dialog open={snapOpen} onOpenChange={(open) => { if (!open) { setSnapOpen(false); resetSnapForm(); } else { setSnapOpen(true); } }}>
                    <DialogTrigger asChild>
                      <Button size="sm" className="bg-slate-900 text-white hover:bg-slate-800">
                        <TrendingUp className="h-4 w-4 mr-2" /> Nouveau Snapshot
                      </Button>
                    </DialogTrigger>
                    <DialogContent className="sm:max-w-[425px]">
                      <DialogHeader>
                        <DialogTitle className="text-2xl font-bold">{editSnapId ? "Modifier le snapshot" : "Mettre à jour la valeur"}</DialogTitle>
                        <DialogDescription>Définissez la valeur actuelle de votre support d'investissement.</DialogDescription>
                      </DialogHeader>
                      <div className="grid gap-6 py-6">
                        <div className="grid gap-2">
                          <Label htmlFor="sdate" className="text-xs uppercase tracking-wider font-bold text-slate-500">Date</Label>
                          <Input id="sdate" type="date" value={snapDate} onChange={(e) => setSnapDate(e.target.value)} className="bg-slate-50 border-slate-200" />
                        </div>
                        <div className="grid gap-2">
                          <Label htmlFor="sval" className="text-xs uppercase tracking-wider font-bold text-slate-500">Valeur Actuelle ({account?.currency || "EUR"})</Label>
                          <Input id="sval" type="number" step="0.01" value={snapValue} onChange={(e) => setSnapValue(e.target.value)} placeholder="0.00" className="bg-slate-50 border-slate-200 font-bold text-lg" />
                        </div>
                        <div className="grid gap-2">
                          <Label htmlFor="snote" className="text-xs uppercase tracking-wider font-bold text-slate-500">Note (Optionnel)</Label>
                          <Input id="snote" value={snapNote} onChange={(e) => setSnapNote(e.target.value)} placeholder="Ex: Point mensuel..." className="bg-slate-50 border-slate-200" />
                        </div>
                      </div>
                      <DialogFooter>
                        <Button variant="ghost" onClick={() => { setSnapOpen(false); resetSnapForm(); }}>Annuler</Button>
                        <Button onClick={handleCreateSnapshot} className="bg-slate-900 text-white shadow-lg">Mettre à jour</Button>
                      </DialogFooter>
                    </DialogContent>
                  </Dialog>

                  <Dialog open={zeroOpen} onOpenChange={(open) => { if (!open) { setZeroOpen(false); resetZeroForm(); } else { setZeroOpen(true); } }}>
                    <DialogTrigger asChild>
                      <Button variant="ghost" size="sm" className="text-slate-500 hover:text-slate-900">
                        <Target className="h-4 w-4 mr-2" /> Nouveau point zéro
                      </Button>
                    </DialogTrigger>
                    <DialogContent className="sm:max-w-[425px]">
                      <DialogHeader>
                        <DialogTitle className="text-2xl font-bold text-rose-600">Nouveau point zéro</DialogTitle>
                        <DialogDescription>
                          Attention : Définir un nouveau point zéro archivera la performance passée. Les calculs de performance repartiront de cette valeur.
                        </DialogDescription>
                      </DialogHeader>
                      <div className="grid gap-6 py-6">
                        <div className="grid gap-2">
                          <Label htmlFor="zdate" className="text-xs uppercase tracking-wider font-bold text-slate-500">Date d'effet</Label>
                          <Input id="zdate" type="date" value={zeroDate} onChange={(e) => setZeroDate(e.target.value)} className="bg-slate-50 border-slate-200" />
                        </div>
                        <div className="grid gap-2">
                          <Label htmlFor="zval" className="text-xs uppercase tracking-wider font-bold text-slate-500">Valeur de référence ({account?.currency || "EUR"})</Label>
                          <Input id="zval" type="number" step="0.01" value={zeroValue} onChange={(e) => setZeroValue(e.target.value)} placeholder="0.00" className="bg-slate-50 border-slate-200 font-bold text-lg" />
                        </div>
                        <div className="grid gap-2">
                          <Label htmlFor="znote" className="text-xs uppercase tracking-wider font-bold text-slate-500">Motif du reset</Label>
                          <Input id="znote" value={zeroNote} onChange={(e) => setZeroNote(e.target.value)} placeholder="Ex: Début de l'année 2026..." className="bg-slate-50 border-slate-200" />
                        </div>
                      </div>
                      <DialogFooter>
                        <Button variant="ghost" onClick={() => { setZeroOpen(false); resetZeroForm(); }}>Annuler</Button>
                        <Button onClick={handleSetZeroPoint} className="bg-rose-600 text-white hover:bg-rose-700 shadow-lg">Réinitialiser la base</Button>
                      </DialogFooter>
                    </DialogContent>
                  </Dialog>
                </>
              )}
            </div>
          </div>
        </div>

        {/* Filter Bar */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4 bg-white p-3 rounded-2xl border border-slate-100 shadow-sm">
          <div className="flex items-center gap-2 text-slate-400 mr-2">
            <Filter className="h-4 w-4" />
            <span className="text-xs font-bold uppercase tracking-wider">Filtres</span>
          </div>
          
          <div className="flex flex-wrap items-center gap-3">
            <Select onValueChange={handleQuickFilter}>
              <SelectTrigger className="w-[140px] h-9 bg-slate-50 border-slate-200 text-xs font-medium">
                <SelectValue placeholder="Période rapide" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Tout l'historique</SelectItem>
                <SelectItem value="current-month">Ce mois-ci</SelectItem>
                <SelectItem value="last-3-months">3 derniers mois</SelectItem>
                <SelectItem value="current-year">Cette année</SelectItem>
              </SelectContent>
            </Select>

            <div className="h-4 w-px bg-slate-200 mx-1 hidden sm:block" />

            <div className="flex items-center gap-2 bg-slate-50 rounded-lg border border-slate-200 px-3 py-0.5">
              <Calendar className="h-3.5 w-3.5 text-slate-400" />
              <Input 
                type="date" 
                value={dateStart} 
                onChange={(e) => setDateStart(e.target.value)} 
                className="border-none shadow-none h-8 w-[120px] p-0 text-xs focus-visible:ring-0 bg-transparent font-medium" 
              />
              <span className="text-slate-300 text-[10px] font-bold">À</span>
              <Input 
                type="date" 
                value={dateEnd} 
                onChange={(e) => setDateEnd(e.target.value)} 
                className="border-none shadow-none h-8 w-[120px] p-0 text-xs focus-visible:ring-0 bg-transparent font-medium" 
              />
              {(dateStart || dateEnd) && (
                <Button 
                  variant="ghost" 
                  size="icon" 
                  onClick={() => { setDateStart(""); setDateEnd(""); }} 
                  className="h-6 w-6 text-slate-400 hover:text-rose-500 hover:bg-rose-50 rounded-full"
                >
                  <Plus className="h-4 w-4 rotate-45" />
                </Button>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Account KPIs */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <Card className="border-none shadow-md bg-slate-900 text-white">
          <CardHeader className="pb-2">
            <CardDescription className="text-slate-400 font-medium">Solde Actuel</CardDescription>
            <CardTitle className="text-3xl font-bold">{formatCurrency(currentBalance || 0)}</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-2 text-xs text-slate-400 mt-2">
              <TrendingUp className="h-3 w-3" />
              <span>Dernière mise à jour aujourd'hui</span>
            </div>
          </CardContent>
        </Card>

        {account.type === "assurance_vie" ? (
          <>
            <Card className="shadow-sm border border-slate-100 hover:border-slate-200 transition-all">
              <CardHeader className="pb-2 flex flex-row items-center justify-between space-y-0">
                <CardDescription className="font-medium text-slate-500">Fonds Euro ({account.fonds_euros_pct || 0}%)</CardDescription>
                <Shield className="h-4 w-4 text-emerald-500" />
              </CardHeader>
              <CardContent>
                <CardTitle className="text-2xl font-bold text-slate-900 amount-blur">
                  {formatCurrency((currentBalance || 0) * ((account.fonds_euros_pct || 0) / 100))}
                </CardTitle>
                <p className="text-xs text-slate-400 mt-2">Capital garanti</p>
              </CardContent>
            </Card>
            <Card className="shadow-sm border border-slate-100 hover:border-slate-200 transition-all">
              <CardHeader className="pb-2 flex flex-row items-center justify-between space-y-0">
                <CardDescription className="font-medium text-slate-500">Unités de Compte ({account.fonds_investis_pct || 0}%)</CardDescription>
                <TrendingUp className="h-4 w-4 text-amber-500" />
              </CardHeader>
              <CardContent>
                <CardTitle className="text-2xl font-bold text-slate-900 amount-blur">
                  {formatCurrency((currentBalance || 0) * ((account.fonds_investis_pct || 0) / 100))}
                </CardTitle>
                <p className="text-xs text-slate-400 mt-2">Fonds investis (UC)</p>
              </CardContent>
            </Card>
            <Card className="shadow-sm border border-slate-100 hover:border-slate-200 transition-all">
              <CardHeader className="pb-2 flex flex-row items-center justify-between space-y-0">
                <CardDescription className="font-medium text-slate-500">Plus-value Latente</CardDescription>
                <Activity className={`h-4 w-4 ${((investmentData?.totals?.gain_eur || 0) >= 0) ? "text-emerald-500" : "text-rose-500"}`} />
              </CardHeader>
              <CardContent>
                <CardTitle className={`text-2xl font-bold ${((investmentData?.totals?.gain_eur || 0) >= 0) ? "text-emerald-600" : "text-rose-600"} amount-blur`}>
                  {((investmentData?.totals?.gain_eur || 0) >= 0) ? "+" : ""}{formatCurrency(investmentData?.totals?.gain_eur || 0)}
                </CardTitle>
                <p className="text-xs text-slate-400 mt-2">Evolution du capital</p>
              </CardContent>
            </Card>
          </>
        ) : isInvestment ? (
          <>
            <Card className="shadow-sm">
              <CardHeader className="pb-2 flex flex-row items-center justify-between space-y-0">
                <CardDescription className="font-medium">Net Investi</CardDescription>
                <Target className="h-4 w-4 text-slate-400" />
              </CardHeader>
              <CardContent>
                <CardTitle className="text-2xl font-bold text-slate-900">
                  {formatCurrency(investmentData?.totals?.net_invested || 0)}
                </CardTitle>
                <p className="text-xs text-slate-400 mt-2">Versements - Retraits</p>
              </CardContent>
            </Card>
            <Card className="shadow-sm">
              <CardHeader className="pb-2 flex flex-row items-center justify-between space-y-0">
                <CardDescription className="font-medium">Plus-value Latente</CardDescription>
                <Activity className="h-4 w-4 text-emerald-500" />
              </CardHeader>
              <CardContent>
                <CardTitle className={`text-2xl font-bold ${(investmentData?.totals?.gain_eur || 0) >= 0 ? "text-emerald-600" : "text-rose-600"}`}>
                  {formatCurrency(investmentData?.totals?.gain_eur || 0)}
                </CardTitle>
                <p className="text-xs text-slate-400 mt-2">Evolution du capital</p>
              </CardContent>
            </Card>
            <Card className="shadow-sm">
              <CardHeader className="pb-2 flex flex-row items-center justify-between space-y-0">
                <CardDescription className="font-medium">Performance</CardDescription>
                <Percent className="h-4 w-4 text-slate-400" />
              </CardHeader>
              <CardContent>
                <CardTitle className={`text-2xl font-bold ${(investmentData?.totals?.performance_pct || 0) >= 0 ? "text-emerald-600" : "text-rose-600"}`}>
                  {investmentData?.totals?.performance_pct?.toFixed(2)}%
                </CardTitle>
                <p className="text-xs text-slate-400 mt-2">Rendement global</p>
              </CardContent>
            </Card>
          </>
        ) : (
          <>
            <Card className="shadow-sm">
              <CardHeader className="pb-2 flex flex-row items-center justify-between space-y-0">
                <CardDescription className="font-medium">Total Entrées</CardDescription>
                <ArrowUpRight className="h-4 w-4 text-emerald-500" />
              </CardHeader>
              <CardContent>
                <CardTitle className="text-2xl font-bold text-emerald-600">+{formatCurrency(stats?.totalIn || 0)}</CardTitle>
                <p className="text-xs text-slate-400 mt-2">{(search || dateStart || dateEnd) ? "Sur la sélection" : "Cumul historique"}</p>
              </CardContent>
            </Card>
            <Card className="shadow-sm">
              <CardHeader className="pb-2 flex flex-row items-center justify-between space-y-0">
                <CardDescription className="font-medium">Total Sorties</CardDescription>
                <ArrowDownRight className="h-4 w-4 text-rose-500" />
              </CardHeader>
              <CardContent>
                <CardTitle className="text-2xl font-bold text-rose-600">-{formatCurrency(stats?.totalOut || 0)}</CardTitle>
                <p className="text-xs text-slate-400 mt-2">{(search || dateStart || dateEnd) ? "Sur la sélection" : "Cumul historique"}</p>
              </CardContent>
            </Card>
            <Card className="shadow-sm">
              <CardHeader className="pb-2 flex flex-row items-center justify-between space-y-0">
                <CardDescription className="font-medium">Panier Moyen</CardDescription>
                <Activity className="h-4 w-4 text-slate-400" />
              </CardHeader>
              <CardContent>
                <CardTitle className="text-2xl font-bold">{formatCurrency(stats?.avgTx || 0)}</CardTitle>
                <p className="text-xs text-slate-400 mt-2">Par dépense effectuée</p>
              </CardContent>
            </Card>
          </>
        )}
      </div>

      {tagTotals.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <Card className="col-span-full shadow-sm border-slate-100">
            <CardHeader className="pb-3 border-b border-slate-50 bg-slate-50/30">
              <div className="flex items-center gap-2">
                <Tag className="h-4 w-4 text-slate-400" />
                <CardTitle className="text-sm font-bold uppercase tracking-wider text-slate-500">Dépenses par tag</CardTitle>
              </div>
            </CardHeader>
            <CardContent className="pt-4">
              <div className="flex flex-wrap gap-4">
                {tagTotals.map((t) => (
                  <div key={t.id} className="flex items-center gap-3 p-3 bg-white border border-slate-100 rounded-2xl shadow-sm min-w-[150px]">
                    <div className="h-8 w-8 rounded-full flex items-center justify-center" style={{ backgroundColor: t.color || "#64748b" }}>
                      <Tag className="h-4 w-4 text-white" />
                    </div>
                    <div>
                      <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400 leading-none mb-1">{t.name}</p>
                      <p className="text-lg font-black text-slate-900 leading-none">{formatCurrency(t.total_eur)}</p>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Charts Section */}
      <div className="w-full space-y-8">
        <Card className="shadow-sm overflow-hidden border-slate-100 w-full">
          <CardHeader className="bg-slate-50/50 border-b pb-4 flex flex-row items-center justify-between">
            <div>
              <CardTitle className="text-lg font-bold">{isInvestment ? "Évolution du capital" : "Évolution du solde"}</CardTitle>
              <CardDescription>Historique complet en temps réel.</CardDescription>
            </div>
            <div className="flex items-center gap-2">
              <Badge variant="outline" className="bg-white">Vue d'ensemble</Badge>
            </div>
          </CardHeader>
          <CardContent className="p-0 h-[300px] md:h-[450px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              {isInvestment ? (
                <AreaChart data={investmentData?.value_series || []} margin={{ top: 20, right: 0, left: 0, bottom: 0 }}>
                  <defs>
                    <linearGradient id="colorInv" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#0f172a" stopOpacity={0.1}/><stop offset="95%" stopColor="#0f172a" stopOpacity={0}/></linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                  <XAxis dataKey="date" axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: '#94a3b8' }} tickFormatter={(val) => format(new Date(val), "dd/MM")} minTickGap={40} />
                  <YAxis hide domain={['auto', 'auto']} />
                  <Tooltip labelFormatter={(val) => format(new Date(val), "PPP", { locale: fr })} formatter={(val: number) => [formatCurrency(val), "Valeur"]} contentStyle={{ borderRadius: "12px", border: "none", boxShadow: "0 10px 15px -3px rgb(0 0 0 / 0.1)" }} />
                  <Area type="monotone" dataKey="current_value" stroke="#0f172a" fillOpacity={1} fill="url(#colorInv)" strokeWidth={4} />
                </AreaChart>
              ) : (
                <AreaChart data={timeseries?.balance_points || []} margin={{ top: 20, right: 0, left: 0, bottom: 0 }}>
                  <defs>
                    <linearGradient id="colorBalance" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#0f172a" stopOpacity={0.1}/><stop offset="95%" stopColor="#0f172a" stopOpacity={0}/></linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                  <XAxis dataKey="date" axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: '#94a3b8' }} tickFormatter={(val) => format(new Date(val), "dd/MM")} minTickGap={40} />
                  <YAxis hide domain={['auto', 'auto']} />
                  <Tooltip labelFormatter={(val) => format(new Date(val), "PPP", { locale: fr })} formatter={(val: number) => [formatCurrency(val), "Solde"]} contentStyle={{ borderRadius: "12px", border: "none", boxShadow: "0 10px 15px -3px rgb(0 0 0 / 0.1)" }} />
                  <Area type="monotone" dataKey="running_balance" stroke="#0f172a" fillOpacity={1} fill="url(#colorBalance)" strokeWidth={4} />
                </AreaChart>
              )}
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {isInvestment && (
          <Card className="shadow-sm overflow-hidden border-slate-100 w-full">
            <CardHeader className="bg-slate-50/50 border-b pb-4 flex flex-row items-center justify-between">
              <div>
                <CardTitle className="text-lg font-bold">Plus-value latente (€)</CardTitle>
                <CardDescription>Évolution des gains ou pertes cumulés.</CardDescription>
              </div>
              <Activity className="h-4 w-4 text-slate-400" />
            </CardHeader>
            <CardContent className="p-0 h-[250px] md:h-[350px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={perfHistory} margin={{ top: 20, right: 0, left: 0, bottom: 0 }}>
                  <defs>
                    <linearGradient id="colorPerf" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#10b981" stopOpacity={0.1}/><stop offset="95%" stopColor="#10b981" stopOpacity={0}/></linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                  <XAxis dataKey="date" axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: '#94a3b8' }} tickFormatter={(val) => format(new Date(val), "dd/MM")} minTickGap={40} />
                  <YAxis hide domain={['auto', 'auto']} />
                  <Tooltip labelFormatter={(val) => format(new Date(val), "PPP", { locale: fr })} formatter={(val: number) => [formatCurrency(val), "Performance"]} contentStyle={{ borderRadius: "12px", border: "none", boxShadow: "0 10px 15px -3px rgb(0 0 0 / 0.1)" }} />
                  <Area type="monotone" dataKey="gain_eur" stroke="#10b981" fillOpacity={1} fill="url(#colorPerf)" strokeWidth={4} />
                </AreaChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Transactions Table Section */}
      {!isInvestment && (
        <div className="space-y-4">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <h2 className="text-xl font-bold text-slate-900 flex items-center gap-2"><History className="h-5 w-5 text-slate-400" /> Historique</h2>
            <div className="flex flex-wrap items-center gap-3">
              <Select value={filterType} onValueChange={setFilterType}>
                <SelectTrigger className="w-[120px] bg-white h-9">
                  <SelectValue placeholder="Type" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Tous types</SelectItem>
                  <SelectItem value="Sortie">Sortie</SelectItem>
                  <SelectItem value="Entree">Entrée</SelectItem>
                  <SelectItem value="Virement">Virement</SelectItem>
                  <SelectItem value="Solde Initial">Solde Initial</SelectItem>
                </SelectContent>
              </Select>

              <Select value={filterCategory} onValueChange={setFilterCategory}>
                <SelectTrigger className="w-[150px] bg-white h-9">
                  <SelectValue placeholder="Catégorie" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Toutes catégories</SelectItem>
                  {categories.map(c => (
                    <SelectItem key={c.id} value={String(c.id)}>{c.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>

              {availableTags.length > 0 && (
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="outline" size="sm" className="h-9 bg-white gap-2">
                      <Tag className="h-4 w-4" />
                      {filterTags.length === 0 ? "Tags" : `${filterTags.length} tags`}
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent className="w-56">
                    <DropdownMenuLabel>Filtrer par tags</DropdownMenuLabel>
                    <DropdownMenuSeparator />
                    {availableTags.map((tag) => (
                      <DropdownMenuCheckboxItem
                        key={tag.id}
                        checked={filterTags.includes(tag.id)}
                        onCheckedChange={(checked) => {
                          if (checked) {
                            setFilterTags([...filterTags, tag.id])
                          } else {
                            setFilterTags(filterTags.filter(id => id !== tag.id))
                          }
                        }}
                      >
                        <div className="flex items-center gap-2">
                          <div className="h-2 w-2 rounded-full" style={{ backgroundColor: tag.color || "#64748b" }} />
                          {tag.name}
                        </div>
                      </DropdownMenuCheckboxItem>
                    ))}
                    {filterTags.length > 0 && (
                      <>
                        <DropdownMenuSeparator />
                        <Button 
                          variant="ghost" 
                          size="sm" 
                          className="w-full text-xs h-8" 
                          onClick={() => setFilterTags([])}
                        >
                          Effacer les filtres
                        </Button>
                      </>
                    )}
                  </DropdownMenuContent>
                </DropdownMenu>
              )}

              <div className="relative w-full md:w-64">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
                <Input placeholder="Rechercher..." className="pl-10 bg-white h-9" value={search} onChange={(e) => setSearch(e.target.value)} />
              </div>
            </div>
          </div>

          <Card className="shadow-sm border-slate-100 overflow-hidden">
            <div className="overflow-x-auto">
              <Table>
                <TableHeader className="bg-slate-50/50">
              <TableRow>
                <TableHead className="w-[50px]">
                  <Checkbox 
                    checked={selectedIds.length === filteredTransactions.length && filteredTransactions.length > 0}
                    onCheckedChange={(checked) => {
                      if (checked) {
                        setSelectedIds(filteredTransactions.map(t => t.id))
                      } else {
                        setSelectedIds([])
                      }
                    }}
                  />
                </TableHead>
                <TableHead className="w-[150px] cursor-pointer hover:bg-slate-100 transition-colors" onClick={() => handleSort("date")}>
                  <div className="flex items-center gap-2">
                    Date
                    {sortField === "date" && (sortOrder === "asc" ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />)}
                  </div>
                </TableHead>
                <TableHead className="cursor-pointer hover:bg-slate-100 transition-colors" onClick={() => handleSort("merchant")}>
                  <div className="flex items-center gap-2">
                    Commerçant
                    {sortField === "merchant" && (sortOrder === "asc" ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />)}
                  </div>
                </TableHead>
                <TableHead className="cursor-pointer hover:bg-slate-100 transition-colors" onClick={() => handleSort("category")}>
                  <div className="flex items-center gap-2">
                    Catégorie / Type
                    {sortField === "category" && (sortOrder === "asc" ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />)}
                  </div>
                </TableHead>
                <TableHead className="text-right cursor-pointer hover:bg-slate-100 transition-colors" onClick={() => handleSort("amount")}>
                  <div className="flex items-center justify-end gap-2">
                    Montant
                    {sortField === "amount" && (sortOrder === "asc" ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />)}
                  </div>
                </TableHead>
                <TableHead className="text-right cursor-pointer hover:bg-slate-100 transition-colors" onClick={() => handleSort("running_balance")}>
                  <div className="flex items-center justify-end gap-2">
                    Solde
                    {sortField === "running_balance" && (sortOrder === "asc" ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />)}
                  </div>
                </TableHead>
                <TableHead className="text-right w-[100px]">Actions</TableHead>
              </TableRow>
            </TableHeader>
              <TableBody>
                {filteredTransactions.map((tx) => (
                  <TableRow key={tx.id}>
                    <TableCell>
                      <Checkbox 
                        checked={selectedIds.includes(tx.id)}
                        onCheckedChange={(checked) => {
                          if (checked) {
                            setSelectedIds(prev => [...prev, tx.id])
                          } else {
                            setSelectedIds(prev => prev.filter(id => id !== tx.id))
                          }
                        }}
                      />
                    </TableCell>
                    <TableCell className="text-xs">{format(new Date(tx.date), "dd/MM/yyyy")}</TableCell>
                    <TableCell title={tx.merchant}>
                      <div className="flex flex-col">
                        <div className="flex items-center gap-1.5">
                          {tx.merchant_obj && (
                            <div className="h-2 w-2 rounded-full shrink-0" style={{ backgroundColor: tx.merchant_obj.color || "#64748b" }} />
                          )}
                          <span className="font-bold text-slate-900">{tx.merchant_obj?.name || tx.merchant}</span>
                          {tx.is_recurring && <Repeat className="h-3 w-3 text-indigo-500" />}
                        </div>
                        {tx.note && <span className="text-[10px] text-slate-400 truncate max-w-[200px]">{tx.note}</span>}
                        {tx.merchant_obj && tx.merchant_obj.name !== tx.merchant && (
                           <span className="text-[9px] text-slate-400 italic truncate max-w-[180px]">{tx.merchant}</span>
                        )}
                        {tx.tags && tx.tags.length > 0 && (
                          <div className="flex flex-wrap gap-1 mt-1">
                            {tx.tags.map(tag => (
                              <Badge 
                                key={tag.id} 
                                className="px-1.5 py-0 text-[8px] font-bold border-none text-white"
                                style={{ backgroundColor: tag.color || "#64748b" }}
                              >
                                {tag.name}
                              </Badge>
                            ))}
                          </div>
                        )}
                      </div>
                    </TableCell>
                    <TableCell>
                      {tx.type === "Solde Initial" ? (
                        <Badge variant="outline" className="bg-slate-100 text-slate-600 border-none">Solde Initial</Badge>
                      ) : tx.type === "Interets" ? (
                        <Badge variant="outline" className="bg-amber-50 text-amber-700 border-none">Intérêts</Badge>
                      ) : (
                        <div className="flex items-center gap-2">
                          <div className="h-6 w-6 rounded-md flex items-center justify-center" style={{ backgroundColor: tx.category?.color || "#f1f5f9" }}>
                            <IconComponent name={tx.category?.icon} className="h-3.5 w-3.5 text-white" />
                          </div>
                          <span className="text-sm font-medium text-slate-600">{tx.category?.name || "Sans catégorie"}</span>
                        </div>
                      )}
                    </TableCell>
                    <TableCell className={`text-right font-bold ${tx.type === "Sortie" ? "text-rose-600" : (tx.type === "Entree" || tx.type === "Interets") ? "text-emerald-600" : "text-slate-900"}`}>
                      <div className="flex flex-col items-end">
                        <span className="amount-blur">
                          {tx.type === "Sortie" ? "-" : (tx.type === "Entree" || tx.type === "Interets") ? "+" : ""}{formatCurrency(tx.amount)}
                        </span>
                        {tx.currency !== account.currency && (
                          <span className="text-[10px] text-slate-400 font-normal amount-blur">
                            ({formatValue(tx.original_amount, tx.currency)})
                          </span>
                        )}
                      </div>
                    </TableCell>
                    <TableCell className="text-right font-extrabold">
                      <span className="amount-blur">{formatCurrency(tx.running_balance)}</span>
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex items-center justify-end gap-1">
                        <Button variant="ghost" size="sm" onClick={() => handleEditTransaction(tx)} className="h-8 w-8 p-0">
                          <Pencil className="h-3.5 w-3.5 text-slate-500" />
                        </Button>
                        <Button variant="ghost" size="sm" onClick={() => handleDeleteTransaction(tx.id)} className="h-8 w-8 p-0">
                          <Trash2 className="h-3.5 w-3.5 text-rose-500" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            </div>
          </Card>
        </div>
      )}

      {isInvestment && (
        <div className="grid gap-8 lg:grid-cols-2">
           <Card className="shadow-sm">
             <CardHeader><CardTitle className="text-lg">Historique des flux</CardTitle></CardHeader>
             <CardContent className="p-0">
               <div className="overflow-x-auto">
                 <Table>                 <TableHeader>
                   <TableRow>
                     <TableHead className="cursor-pointer hover:bg-slate-100 transition-colors" onClick={() => handleInvSort("date")}>
                       <div className="flex items-center gap-2">
                         Date
                         {invSortField === "date" && (invSortOrder === "asc" ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />)}
                       </div>
                     </TableHead>
                     <TableHead className="cursor-pointer hover:bg-slate-100 transition-colors" onClick={() => handleInvSort("type")}>
                       <div className="flex items-center gap-2">
                         Libellé / Type
                         {invSortField === "type" && (invSortOrder === "asc" ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />)}
                       </div>
                     </TableHead>
                     <TableHead className="text-right cursor-pointer hover:bg-slate-100 transition-colors" onClick={() => handleInvSort("amount")}>
                       <div className="flex items-center justify-end gap-2">
                         Montant
                         {invSortField === "amount" && (invSortOrder === "asc" ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />)}
                       </div>
                     </TableHead>
                     <TableHead className="text-right w-[80px]">Actions</TableHead>
                   </TableRow>
                 </TableHeader>
                  <TableBody>
                   {sortedInvestmentTransactions.map((tx: any) => (
                     <TableRow key={tx.id + (tx.is_regular ? "-reg" : "-inv")}>
                       <TableCell className="text-xs">{format(new Date(tx.date), "dd/MM/yyyy")}</TableCell>
                       <TableCell>
                         <div className="flex flex-col gap-1">
                           <Badge variant="outline" className="capitalize w-fit">{tx.type}</Badge>
                           {tx.note && <span className="text-[10px] text-slate-500 line-clamp-1">{tx.note}</span>}
                         </div>
                       </TableCell>
                       <TableCell className="text-right font-bold">
                         <div className="flex flex-col items-end">
                           <span className="amount-blur">{formatCurrency(tx.amount)}</span>
                           {tx.currency && tx.currency !== account.currency && (
                             <span className="text-[10px] text-slate-400 font-normal amount-blur">
                               ({formatValue(tx.original_amount || tx.amount, tx.currency)})
                             </span>
                           )}
                         </div>
                       </TableCell>
                       <TableCell className="text-right">
                          {!tx.is_regular && (
                            <div className="flex items-center justify-end gap-1">
                              <Button variant="ghost" size="sm" onClick={() => handleEditInvTransaction(tx)} className="h-8 w-8 p-0"><Pencil className="h-3 w-3" /></Button>
                              <Button variant="ghost" size="sm" onClick={() => handleDeleteInvTransaction(tx.id)} className="h-8 w-8 p-0 text-rose-500"><Trash2 className="h-3 w-3" /></Button>
                            </div>
                          )}
                       </TableCell>
                     </TableRow>
                   ))}
                   {(investmentData?.transactions || []).length === 0 && (
                     <TableRow><TableCell colSpan={4} className="text-center py-10 text-slate-400">Aucun flux enregistré.</TableCell></TableRow>
                   )}
                 </TableBody>
               </Table>
            </div>
             </CardContent>
           </Card>
           <Card className="shadow-sm">
             <CardHeader><CardTitle className="text-lg">Derniers Snapshots</CardTitle></CardHeader>
             <CardContent className="p-0">
               <div className="overflow-x-auto">
                 <Table>                 <TableHeader>
                   <TableRow>
                     <TableHead className="cursor-pointer hover:bg-slate-100 transition-colors" onClick={() => handleSnapSort("date")}>
                       <div className="flex items-center gap-2">
                         Date
                         {snapSortField === "date" && (snapSortOrder === "asc" ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />)}
                       </div>
                     </TableHead>
                     <TableHead className="text-right cursor-pointer hover:bg-slate-100 transition-colors" onClick={() => handleSnapSort("current_value")}>
                       <div className="flex items-center justify-end gap-2">
                         Valeur
                         {snapSortField === "current_value" && (snapSortOrder === "asc" ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />)}
                       </div>
                     </TableHead>
                     <TableHead className="text-right w-[80px]">Actions</TableHead>
                   </TableRow>
                 </TableHeader>
                 <TableBody>
                   {sortedSnapshots.map((snap: any) => (
                     <TableRow key={snap.id}>
                       <TableCell className="text-xs">{format(new Date(snap.date), "dd/MM/yyyy")}</TableCell>
                       <TableCell className="text-right font-bold">
                         <span className="amount-blur">{formatCurrency(snap.current_value)}</span>
                       </TableCell>
                       <TableCell className="text-right">
                          <div className="flex items-center justify-end gap-1">
                            <Button variant="ghost" size="sm" onClick={() => handleEditSnapshot(snap)} className="h-8 w-8 p-0"><Pencil className="h-3 w-3" /></Button>
                            <Button variant="ghost" size="sm" onClick={() => handleDeleteSnapshot(snap.id)} className="h-8 w-8 p-0 text-rose-500"><Trash2 className="h-3 w-3" /></Button>
                          </div>
                       </TableCell>
                     </TableRow>
                   ))}
                 </TableBody>
               </Table>
            </div>
             </CardContent>
           </Card>

        </div>
      )}
      {/* Bulk Actions Floating Bar */}
      {selectedIds.length > 0 && (
        <div className="fixed bottom-8 left-1/2 -translate-x-1/2 z-50 bg-slate-900 text-white px-6 py-4 rounded-2xl shadow-2xl border border-slate-800 flex items-center gap-6 animate-in fade-in slide-in-from-bottom-4 duration-300">
          <div className="flex items-center gap-2 pr-4 border-r border-slate-700">
            <Badge className="bg-emerald-500 text-white border-none">{selectedIds.length}</Badge>
            <span className="text-sm font-medium">sélectionnés</span>
          </div>
          
          <div className="flex items-center gap-2">
            <Button 
              size="sm" 
              variant="ghost" 
              className="text-white hover:bg-slate-800 gap-2"
              onClick={() => setIsBulkEditDialogOpen(true)}
            >
              <Pencil className="h-4 w-4" />
              Modifier
            </Button>
            
            <Button 
              size="sm" 
              variant="ghost" 
              className="text-rose-400 hover:text-rose-300 hover:bg-rose-500/10 gap-2"
              onClick={async () => {
                if (confirm(`Supprimer ${selectedIds.length} transactions ?`)) {
                  try {
                    await Promise.all(selectedIds.map(id => api.delete(`/transactions/${id}`)))
                    toast.success(`${selectedIds.length} transactions supprimées`)
                    setSelectedIds([])
                    await loadData()
                  } catch (e) {
                    toast.error("Erreur lors de la suppression groupée")
                  }
                }
              }}
            >
              <Trash2 className="h-4 w-4" />
              Supprimer
            </Button>
          </div>

          <Separator orientation="vertical" className="h-6 bg-slate-700" />

          <Button 
            size="sm" 
            variant="ghost" 
            className="text-slate-400 hover:text-white p-2"
            onClick={() => setSelectedIds([])}
          >
            <X className="h-4 w-4" />
          </Button>
        </div>
      )}

      {/* Bulk Edit Dialog */}
      <Dialog open={isBulkEditDialogOpen} onOpenChange={setIsBulkEditDialogOpen}>
        <DialogContent className="sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle>Modification groupée</DialogTitle>
            <DialogDescription>
              Appliquer ces changements aux {selectedIds.length} transactions sélectionnées.
            </DialogDescription>
          </DialogHeader>
          
          <div className="grid gap-6 py-4">
            <div className="space-y-2">
              <Label>Catégorie</Label>
              <Select value={bulkCategory} onValueChange={setBulkCategory}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="keep">Ne pas changer</SelectItem>
                  <SelectItem value="none">Aucune catégorie</SelectItem>
                  {categories.map((cat) => (
                    <SelectItem key={cat.id} value={String(cat.id)}>
                      <div className="flex items-center gap-2">
                        <div className="h-3 w-3 rounded-full" style={{ backgroundColor: cat.color || "#cbd5e1" }} />
                        {cat.name}
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>Caractère récurrent</Label>
              <Select value={bulkRecurring} onValueChange={setBulkRecurring}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="keep">Ne pas changer</SelectItem>
                  <SelectItem value="true">Récurrente</SelectItem>
                  <SelectItem value="false">Ponctuelle</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-4 pt-2 border-t">
              <div className="flex items-center justify-between">
                <Label>Tags</Label>
                <Select value={bulkTagAction} onValueChange={(v: any) => setBulkTagAction(v)}>
                  <SelectTrigger className="w-[150px] h-8 text-xs">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="keep">Ne pas changer</SelectItem>
                    <SelectItem value="replace">Remplacer par...</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {bulkTagAction === "replace" && (
                <div className="flex flex-wrap gap-2 p-3 bg-slate-50 rounded-xl border border-slate-200">
                  {availableTags.map((tag) => (
                    <div key={tag.id} className="flex items-center space-x-2">
                      <Checkbox 
                        id={`bulk-tag-${tag.id}`} 
                        checked={bulkTagIds.includes(tag.id)}
                        onCheckedChange={(checked) => {
                          if (checked) {
                            setBulkTagIds([...bulkTagIds, tag.id])
                          } else {
                            setBulkTagIds(bulkTagIds.filter(tid => tid !== tag.id))
                          }
                        }}
                      />
                      <label
                        htmlFor={`bulk-tag-${tag.id}`}
                        className="text-xs font-medium leading-none cursor-pointer"
                      >
                        <Badge 
                          variant="outline" 
                          className="px-2 py-0 h-5 border-none text-white font-bold text-[9px]"
                          style={{ backgroundColor: tag.color || "#64748b" }}
                        >
                          {tag.name}
                        </Badge>
                      </label>
                    </div>
                  ))}
                  {availableTags.length === 0 && (
                    <p className="text-[10px] text-slate-400">Aucun tag disponible.</p>
                  )}
                </div>
              )}
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setIsBulkEditDialogOpen(false)}>Annuler</Button>
            <Button onClick={handleBulkUpdate} className="bg-slate-900 text-white">Appliquer</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
