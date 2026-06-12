import { useState, useEffect } from "react"
import { useSearchParams } from "react-router-dom"
import { 
  Plus, 
  Settings as SettingsIcon,
  Tag,
  Palette,
  Trash2,
  Download,
  Database,
  Pencil,
  AlertTriangle,
  ArrowRight,
  ArrowRightLeft,
  Upload,
  Coffee,
  ShoppingBag,
  Car,
  Home,
  Heart,
  Zap,
  Music,
  Utensils,
  Smartphone,
  Plane,
  Gift,
  Briefcase,
  CreditCard,
  Wallet,
  Banknote,
  Trophy,
  Activity,
  User,
  Film,
  Dumbbell,
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
  Search,
  Shield,
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
  Target,
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
  Filter
} from "lucide-react"
import { api, API_BASE } from "@/lib/api"
import { RulesTab } from "@/components/settings/RulesTab"
import { TransfersTab } from "@/components/settings/TransfersTab"
import { TagsTab } from "@/components/settings/TagsTab"
import { AccountTab } from "@/components/settings/AccountTab"
import { Button } from "@/components/ui/button"
import { 
  Card, 
  CardContent, 
  CardDescription, 
  CardHeader, 
  CardTitle 
} from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
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
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { toast } from "sonner"
import { Badge } from "@/components/ui/badge"

import { Checkbox } from "@/components/ui/checkbox"
import { ImportTab } from "@/components/settings/ImportTab"

const ICON_OPTIONS = [
  { name: "Coffee", icon: Coffee },
  { name: "ShoppingBag", icon: ShoppingBag },
  { name: "Utensils", icon: Utensils },
  { name: "Car", icon: Car },
  { name: "Home", icon: Home },
  { name: "Heart", icon: Heart },
  { name: "Zap", icon: Zap },
  { name: "Music", icon: Music },
  { name: "Smartphone", icon: Smartphone },
  { name: "Plane", icon: Plane },
  { name: "Gift", icon: Gift },
  { name: "Briefcase", icon: Briefcase },
  { name: "CreditCard", icon: CreditCard },
  { name: "Wallet", icon: Wallet },
  { name: "Banknote", icon: Banknote },
  { name: "Trophy", icon: Trophy },
  { name: "Activity", icon: Activity },
  { name: "User", icon: User },
  { name: "Film", icon: Film },
  { name: "Dumbbell", icon: Dumbbell },
  { name: "Airplay", icon: Airplay },
  { name: "AlarmClock", icon: AlarmClock },
  { name: "Archive", icon: Archive },
  { name: "Award", icon: Award },
  { name: "Backpack", icon: Backpack },
  { name: "Bath", icon: Bath },
  { name: "Beer", icon: Beer },
  { name: "Bell", icon: Bell },
  { name: "Bike", icon: Bike },
  { name: "Book", icon: Book },
  { name: "Box", icon: Box },
  { name: "Camera", icon: Camera },
  { name: "Clapperboard", icon: Clapperboard },
  { name: "Cloud", icon: Cloud },
  { name: "Compass", icon: Compass },
  { name: "Cookie", icon: Cookie },
  { name: "Cpu", icon: Cpu },
  { name: "Dice5", icon: Dice5 },
  { name: "Dog", icon: Dog },
  { name: "Droplet", icon: Droplet },
  { name: "Egg", icon: Egg },
  { name: "Eye", icon: Eye },
  { name: "Fan", icon: Fan },
  { name: "Feather", icon: Feather },
  { name: "Fish", icon: Fish },
  { name: "Flag", icon: Flag },
  { name: "Flashlight", icon: Flashlight },
  { name: "FlaskConical", icon: FlaskConical },
  { name: "Flower", icon: Flower },
  { name: "Footprints", icon: Footprints },
  { name: "Fuel", icon: Fuel },
  { name: "Gamepad2", icon: Gamepad2 },
  { name: "GlassWater", icon: GlassWater },
  { name: "Globe", icon: Globe },
  { name: "Grape", icon: Grape },
  { name: "Hammer", icon: Hammer },
  { name: "IceCream", icon: IceCream },
  { name: "Key", icon: Key },
  { name: "Laptop", icon: Laptop },
  { name: "Library", icon: Library },
  { name: "Lightbulb", icon: Lightbulb },
  { name: "Locate", icon: Locate },
  { name: "Lock", icon: Lock },
  { name: "Map", icon: Map },
  { name: "Mic", icon: Mic },
  { name: "Monitor", icon: Monitor },
  { name: "Moon", icon: Moon },
  { name: "Mountain", icon: Mountain },
  { name: "Mouse", icon: Mouse },
  { name: "Network", icon: Network },
  { name: "Newspaper", icon: Newspaper },
  { name: "Nut", icon: Nut },
  { name: "Package", icon: Package },
  { name: "Paintbrush", icon: Paintbrush },
  { name: "Palmtree", icon: Palmtree },
  { name: "Paperclip", icon: Paperclip },
  { name: "PawPrint", icon: PawPrint },
  { name: "Phone", icon: Phone },
  { name: "Pizza", icon: Pizza },
  { name: "Plug", icon: Plug },
  { name: "Printer", icon: Printer },
  { name: "Puzzle", icon: Puzzle },
  { name: "Radio", icon: Radio },
  { name: "Receipt", icon: Receipt },
  { name: "Recycle", icon: Recycle },
  { name: "Rocket", icon: Rocket },
  { name: "Route", icon: Route },
  { name: "Rss", icon: Rss },
  { name: "Sailboat", icon: Sailboat },
  { name: "Scissors", icon: Scissors },
  { name: "ScreenShare", icon: ScreenShare },
  { name: "Search", icon: Search },
  { name: "Settings", icon: SettingsIcon },
  { name: "Shield", icon: Shield },
  { name: "Ship", icon: Ship },
  { name: "Shirt", icon: Shirt },
  { name: "ShowerHead", icon: ShowerHead },
  { name: "Skull", icon: Skull },
  { name: "Smile", icon: Smile },
  { name: "Snowflake", icon: Snowflake },
  { name: "Speaker", icon: Speaker },
  { name: "Sprout", icon: Sprout },
  { name: "Stamp", icon: Stamp },
  { name: "Star", icon: Star },
  { name: "Stethoscope", icon: Stethoscope },
  { name: "Sun", icon: Sun },
  { name: "Sunrise", icon: Sunrise },
  { name: "Sunset", icon: Sunset },
  { name: "Tablet", icon: Tablet },
  { name: "Target", icon: Target },
  { name: "Tent", icon: Tent },
  { name: "Terminal", icon: Terminal },
  { name: "Thermometer", icon: Thermometer },
  { name: "Ticket", icon: Ticket },
  { name: "Timer", icon: Timer },
  { name: "Train", icon: Train },
  { name: "Trash", icon: Trash },
  { name: "TreeDeciduous", icon: TreeDeciduous },
  { name: "TreePine", icon: TreePine },
  { name: "Trees", icon: Trees },
  { name: "Tv", icon: Tv },
  { name: "Umbrella", icon: Umbrella },
  { name: "UtilityPole", icon: UtilityPole },
  { name: "Variable", icon: Variable },
  { name: "Video", icon: Video },
  { name: "Voicemail", icon: Voicemail },
  { name: "Volume2", icon: Volume2 },
  { name: "Watch", icon: Watch },
  { name: "Waves", icon: Waves },
  { name: "Webcam", icon: Webcam },
  { name: "Weight", icon: Weight },
  { name: "Wifi", icon: Wifi },
  { name: "Wind", icon: Wind },
  { name: "Wine", icon: Wine },
  { name: "Wrench", icon: Wrench },
]

const COLOR_OPTIONS = [
  { name: "Emerald", value: "#10b981" },
  { name: "Blue", value: "#3b82f6" },
  { name: "Indigo", value: "#6366f1" },
  { name: "Violet", value: "#8b5cf6" },
  { name: "Pink", value: "#ec4899" },
  { name: "Rose", value: "#f43f5e" },
  { name: "Orange", value: "#f97316" },
  { name: "Amber", value: "#f59e0b" },
  { name: "Slate", value: "#64748b" },
  { name: "Black", value: "#0f172a" },
]

type Category = {
  id: number
  name: string
  type: "depense" | "revenu" | "neutre"
  icon?: string
  color?: string
  group?: string | null
  monthly_limit?: number | null
  annual_limit?: number | null
}

type Account = {
  id: number
  name: string
  type: string
  active: boolean
}

const ICON_MAP: Record<string, any> = {
  Coffee, ShoppingBag, Utensils, Car, Home, Heart, Zap, Music, Smartphone, Plane, Gift, 
  Briefcase, CreditCard, Wallet, Banknote, ArrowRightLeft,
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

export default function Settings() {
  const [searchParams] = useSearchParams()
  const defaultTab = searchParams.get("tab") || "categories"
  
  const [categories, setCategories] = useState<Category[]>([])
  const [accounts, setAccounts] = useState<Account[]>([])
  const [selectedAccounts, setSelectedAccounts] = useState<number[]>([])
  const [loading, setLoading] = useState(true)
  
  // -- New Category Form --
  const [newOpen, setNewOpen] = useState(false)
  const [newCatName, setNewCatName] = useState("")
  const [newCatType, setNewCatType] = useState<"depense" | "revenu" | "neutre">("depense")
  const [newCatIcon, setNewCatIcon] = useState("Tag")
  const [newCatColor, setNewCatColor] = useState("#64748b")
  const [newCatGroup, setNewCatGroup] = useState("")
  const [newMonthlyLimit, setNewMonthlyLimit] = useState("")
  const [newAnnualLimit, setNewAnnualLimit] = useState("")

  // -- Edit Category Form --
  const [editOpen, setEditOpen] = useState(false)
  const [editingCat, setEditingCat] = useState<Category | null>(null)
  const [editCatName, setEditCatName] = useState("")
  const [editCatType, setEditCatType] = useState<"depense" | "revenu" | "neutre">("depense")
  const [editCatIcon, setEditCatIcon] = useState("Tag")
  const [editCatColor, setEditCatColor] = useState("#64748b")
  const [editCatGroup, setEditCatGroup] = useState("")
  const [editMonthlyLimit, setEditMonthlyLimit] = useState("")
  const [editAnnualLimit, setEditAnnualLimit] = useState("")

  // -- System State --
  const [resetOpen, setResetOpen] = useState(false)
  const [resetConfirmText, setResetConfirmText] = useState("")

  const loadCategories = async () => {
    try {
      const data = await api.get<Category[]>("/categories")
      setCategories(data)
    } catch (error) {
      toast.error("Erreur chargement catégories")
    } finally {
      setLoading(false)
    }
  }

  const loadAccounts = async () => {
    try {
      const data = await api.get<Account[]>("/accounts")
      const activeAccounts = data.filter((a) => a.active)
      setAccounts(activeAccounts)
      // Par défaut, on sélectionne tout
      setSelectedAccounts(activeAccounts.map(a => a.id))
    } catch (error) {
      console.error("Erreur chargement comptes", error)
    }
  }

  useEffect(() => {
    loadCategories()
    loadAccounts()
  }, [])

  const handleAddCategory = async () => {
    if (!newCatName) return
    try {
      await api.post("/categories", {
        name: newCatName,
        type: newCatType,
        icon: newCatIcon,
        color: newCatColor,
        group: newCatGroup || null,
        monthly_limit: newMonthlyLimit ? parseFloat(newMonthlyLimit) : null,
        annual_limit: newAnnualLimit ? parseFloat(newAnnualLimit) : null,
      })
      toast.success("Catégorie ajoutée")
      setNewCatName("")
      setNewCatType("depense")
      setNewCatIcon("Tag")
      setNewCatColor("#64748b")
      setNewCatGroup("")
      setNewMonthlyLimit("")
      setNewAnnualLimit("")
      setNewOpen(false)
      loadCategories()
    } catch (error) {
      toast.error("Erreur lors de l'ajout")
    }
  }

  const handleEditClick = (cat: Category) => {
    setEditingCat(cat)
    setEditCatName(cat.name)
    setEditCatType(cat.type)
    setEditCatIcon(cat.icon || "Tag")
    setEditCatColor(cat.color || "#64748b")
    setEditCatGroup(cat.group || "")
    setEditMonthlyLimit(cat.monthly_limit != null ? String(cat.monthly_limit) : "")
    setEditAnnualLimit(cat.annual_limit != null ? String(cat.annual_limit) : "")
    setEditOpen(true)
  }

  const handleUpdateCategory = async () => {
    if (!editingCat || !editCatName) return
    try {
      await api.patch(`/categories/${editingCat.id}`, {
        name: editCatName,
        type: editCatType,
        icon: editCatIcon,
        color: editCatColor,
        group: editCatGroup || null,
        monthly_limit: editMonthlyLimit ? parseFloat(editMonthlyLimit) : null,
        annual_limit: editAnnualLimit ? parseFloat(editAnnualLimit) : null,
      })
      toast.success("Catégorie mise à jour")
      setEditOpen(false)
      loadCategories()
    } catch (error) {
      toast.error("Erreur lors de la mise à jour")
    }
  }

  const handleDeleteCategory = async (categoryId: number) => {
    if (!confirm("Supprimer cette catégorie ? Les transactions associées n'auront plus de catégorie.")) return
    try {
      await api.delete(`/categories/${categoryId}`)
      toast.success("Catégorie supprimée")
      loadCategories()
    } catch (error) {
      toast.error("Erreur lors de la suppression")
    }
  }

  const handleExport = () => {
    // Direct download via window.location for CSV files
    const params = new URLSearchParams()
    if (selectedAccounts.length > 0) {
      params.append("account_ids", selectedAccounts.join(","))
    }
    window.location.href = `${API_BASE}/export/transactions.csv?${params.toString()}`;
  }

  return (
    <div className="space-y-10 pb-10">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-4xl font-extrabold tracking-tight text-slate-900">Paramètres</h1>
          <p className="text-slate-500 mt-1">Personnalisez votre expérience et gérez vos données.</p>
        </div>
      </div>

      <Tabs defaultValue={defaultTab} className="w-full">
        <div className="overflow-x-auto pb-2 [ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
          <TabsList className="bg-slate-100 p-1 rounded-xl mb-2 sm:mb-8 inline-flex w-full sm:w-auto">
            <TabsTrigger value="account" className="rounded-lg px-6 flex-1 sm:flex-none">
              <User className="h-4 w-4 mr-2" /> Compte
            </TabsTrigger>
            <TabsTrigger value="categories" className="rounded-lg px-6 flex-1 sm:flex-none">
              <Tag className="h-4 w-4 mr-2" /> Catégories
            </TabsTrigger>
            <TabsTrigger value="tags" className="rounded-lg px-6 flex-1 sm:flex-none">
              <Tag className="h-4 w-4 mr-2" /> Tags
            </TabsTrigger>
            <TabsTrigger value="rules" className="rounded-lg px-6 flex-1 sm:flex-none">
              <Filter className="h-4 w-4 mr-2" /> Règles
            </TabsTrigger>
            <TabsTrigger value="transferts" className="rounded-lg px-6 flex-1 sm:flex-none">
              <ArrowRightLeft className="h-4 w-4 mr-2" /> Transferts
            </TabsTrigger>
            <TabsTrigger value="import" className="rounded-lg px-6 flex-1 sm:flex-none">
              <Upload className="h-4 w-4 mr-2" /> Importation
            </TabsTrigger>
            <TabsTrigger value="system" className="rounded-lg px-6 flex-1 sm:flex-none">
              <SettingsIcon className="h-4 w-4 mr-2" /> Système
            </TabsTrigger>
          </TabsList>
        </div>

        <TabsContent value="account">
          <AccountTab />
        </TabsContent>

        <TabsContent value="categories" className="space-y-8">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <h2 className="text-2xl font-bold text-slate-900">Gestion des catégories</h2>
            
            <Dialog open={newOpen} onOpenChange={setNewOpen}>
              <DialogTrigger asChild>
                <Button className="bg-slate-900 text-white hover:bg-slate-800 shadow-lg w-full sm:w-auto">
                  <Plus className="h-4 w-4 mr-2" /> Nouvelle catégorie
                </Button>
              </DialogTrigger>
              <DialogContent className="sm:max-w-[500px]">
                <DialogHeader>
                  <DialogTitle className="text-2xl font-bold">Nouvelle catégorie</DialogTitle>
                  <DialogDescription>
                    Créez une catégorie personnalisée avec son icône et sa couleur.
                  </DialogDescription>
                </DialogHeader>
                <div className="grid gap-6 py-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="grid gap-2">
                      <Label htmlFor="new-name" className="text-xs font-bold uppercase tracking-wider text-slate-500">Nom</Label>
                      <Input 
                        id="new-name" 
                        placeholder="Ex: Streaming..." 
                        value={newCatName}
                        onChange={(e) => setNewCatName(e.target.value)}
                        className="bg-slate-50 border-slate-200"
                      />
                    </div>
                    <div className="grid gap-2">
                      <Label className="text-xs font-bold uppercase tracking-wider text-slate-500">Nature</Label>
                      <Select value={newCatType} onValueChange={(v: any) => setNewCatType(v)}>
                        <SelectTrigger className="bg-slate-50 border-slate-200">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="depense">Dépense (-)</SelectItem>
                          <SelectItem value="revenu">Revenu (+)</SelectItem>
                          <SelectItem value="neutre">Neutre</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </div>

                  <div className="grid gap-2">
                    <Label htmlFor="new-group" className="text-xs font-bold uppercase tracking-wider text-slate-500">Groupe (pour Sankey)</Label>
                    <Input 
                      id="new-group" 
                      placeholder="Ex: Vie courante, Loisirs..." 
                      value={newCatGroup}
                      onChange={(e) => setNewCatGroup(e.target.value)}
                      className="bg-slate-50 border-slate-200"
                    />
                  </div>

                  <div className="grid gap-2">
                    <Label className="text-xs font-bold uppercase tracking-wider text-slate-500">Icône</Label>
                    <div className="p-3 bg-slate-50 rounded-xl border border-slate-200">
                      <div className="grid grid-cols-5 sm:grid-cols-10 gap-2 max-h-[200px] overflow-y-auto pr-2 custom-scrollbar">
                        {ICON_OPTIONS.map((opt) => (
                          <button
                            key={opt.name}
                            type="button"
                            onClick={() => setNewCatIcon(opt.name)}
                            className={`p-2 rounded-lg flex items-center justify-center transition-all ${newCatIcon === opt.name ? 'bg-slate-900 text-white' : 'hover:bg-slate-200 text-slate-500'}`}
                          >
                            <opt.icon className="h-4 w-4" />
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>

                  <div className="grid gap-2">
                    <Label className="text-xs font-bold uppercase tracking-wider text-slate-500">Couleur</Label>
                    <div className="flex flex-wrap gap-2 p-3 bg-slate-50 rounded-xl border border-slate-200 justify-center sm:justify-start">
                      {COLOR_OPTIONS.map((opt) => (
                        <button
                          key={opt.name}
                          type="button"
                          onClick={() => setNewCatColor(opt.value)}
                          className={`h-8 w-8 rounded-full border-4 transition-all ${newCatColor === opt.value ? 'border-slate-300 scale-110' : 'border-transparent hover:scale-105'}`}
                          style={{ backgroundColor: opt.value }}
                          title={opt.name}
                        />
                      ))}
                    </div>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div className="grid gap-2">
                      <Label htmlFor="new-monthly-limit" className="text-xs font-bold uppercase tracking-wider text-slate-500">Limite mensuelle (€)</Label>
                      <Input
                        id="new-monthly-limit"
                        type="number"
                        min="0"
                        placeholder="Ex: 200"
                        value={newMonthlyLimit}
                        onChange={(e) => setNewMonthlyLimit(e.target.value)}
                        className="bg-slate-50 border-slate-200"
                      />
                    </div>
                    <div className="grid gap-2">
                      <Label htmlFor="new-annual-limit" className="text-xs font-bold uppercase tracking-wider text-slate-500">Limite annuelle (€)</Label>
                      <Input
                        id="new-annual-limit"
                        type="number"
                        min="0"
                        placeholder="Ex: 2400"
                        value={newAnnualLimit}
                        onChange={(e) => setNewAnnualLimit(e.target.value)}
                        className="bg-slate-50 border-slate-200"
                      />
                    </div>
                  </div>

                  <div className="flex items-center gap-4 p-4 bg-slate-900 rounded-2xl text-white">
                    <div className="h-10 w-10 rounded-xl flex items-center justify-center" style={{ backgroundColor: newCatColor }}>
                      <IconComponent name={newCatIcon} className="h-6 w-6 text-white" />
                    </div>
                    <div>
                      <p className="text-sm font-bold">{newCatName || "Nom de la catégorie"}</p>
                      <p className="text-[10px] uppercase font-black opacity-50 tracking-widest">{newCatType}</p>
                    </div>
                  </div>
                </div>
                <DialogFooter>
                  <Button variant="ghost" onClick={() => setNewOpen(false)}>Annuler</Button>
                  <Button onClick={handleAddCategory} className="bg-slate-900 text-white shadow-lg">Créer la catégorie</Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </div>

          {loading ? (
             <div className="text-center py-20 text-slate-400">Chargement de vos catégories...</div>
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
              {categories.map((cat) => (
                <Card key={cat.id} className="group hover:border-slate-300 transition-all shadow-sm border-slate-100 overflow-hidden">
                  <CardContent className="p-0">
                    <div className="p-4 flex items-center gap-4">
                      <div className="h-12 w-12 rounded-2xl flex items-center justify-center shadow-sm" style={{ backgroundColor: cat.color || "#f1f5f9" }}>
                        <IconComponent name={cat.icon} className="h-6 w-6 text-white" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="font-bold text-slate-900 truncate">{cat.name}</p>
                        <div className="flex items-center gap-2 mt-1">
                          <Badge variant="outline" className={`
                            text-[9px] uppercase font-black border-none px-0
                            ${cat.type === 'depense' ? 'text-rose-500' : ''}
                            ${cat.type === 'revenu' ? 'text-emerald-500' : ''}
                            ${cat.type === 'neutre' ? 'text-slate-400' : ''}
                          `}>
                            {cat.type}
                          </Badge>
                          {cat.group && (
                            <Badge variant="secondary" className="text-[9px] h-4 px-1 bg-slate-100 text-slate-500 border-none font-bold">
                              {cat.group}
                            </Badge>
                          )}
                        </div>
                        {cat.monthly_limit != null && (
                          <p className="text-[10px] text-amber-600 font-semibold mt-0.5">{cat.monthly_limit}€/mois</p>
                        )}
                      </div>
                    </div>
                    <div className="px-4 py-3 bg-slate-50/50 border-t flex justify-between items-center opacity-0 group-hover:opacity-100 transition-opacity">
                      <p className="text-[10px] text-slate-400 font-medium">ID: #{cat.id}</p>
                      <div className="flex gap-1">
                        <Button variant="ghost" size="sm" onClick={() => handleEditClick(cat)} className="h-8 w-8 p-0 text-slate-500 hover:text-slate-900">
                          <Pencil className="h-4 w-4" />
                        </Button>
                        <Button variant="ghost" size="sm" onClick={() => handleDeleteCategory(cat.id)} className="h-8 w-8 p-0 text-rose-500 hover:text-rose-600 hover:bg-rose-50">
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}

          {/* Edit Dialog */}
          <Dialog open={editOpen} onOpenChange={setEditOpen}>
            <DialogContent className="sm:max-w-[500px]">
              <DialogHeader>
                <DialogTitle className="text-2xl font-bold">Modifier la catégorie</DialogTitle>
                <DialogDescription>Mettez à jour les informations de votre catégorie.</DialogDescription>
              </DialogHeader>
              <div className="grid gap-6 py-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="grid gap-2">
                    <Label htmlFor="edit-name" className="text-xs font-bold uppercase tracking-wider text-slate-500">Nom</Label>
                    <Input 
                      id="edit-name" 
                      value={editCatName}
                      onChange={(e) => setEditCatName(e.target.value)}
                      className="bg-slate-50 border-slate-200"
                    />
                  </div>
                  <div className="grid gap-2">
                    <Label className="text-xs font-bold uppercase tracking-wider text-slate-500">Nature</Label>
                    <Select value={editCatType} onValueChange={(v: any) => setEditCatType(v)}>
                      <SelectTrigger className="bg-slate-50 border-slate-200">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="depense">Dépense (-)</SelectItem>
                        <SelectItem value="revenu">Revenu (+)</SelectItem>
                        <SelectItem value="neutre">Neutre</SelectItem>
                      </SelectContent>
                      </Select>
                      </div>
                      </div>

                      <div className="grid gap-2">
                      <Label htmlFor="edit-group" className="text-xs font-bold uppercase tracking-wider text-slate-500">Groupe (pour Sankey)</Label>
                      <Input 
                      id="edit-group" 
                      placeholder="Ex: Vie courante, Loisirs..." 
                      value={editCatGroup}
                      onChange={(e) => setEditCatGroup(e.target.value)}
                      className="bg-slate-50 border-slate-200"
                      />
                      </div>

                      <div className="grid gap-2">
                      <Label className="text-xs font-bold uppercase tracking-wider text-slate-500">Icône</Label>

                  <div className="p-3 bg-slate-50 rounded-xl border border-slate-200">
                    <div className="grid grid-cols-10 gap-2 max-h-[200px] overflow-y-auto pr-2 custom-scrollbar">
                      {ICON_OPTIONS.map((opt) => (
                        <button
                          key={opt.name}
                          type="button"
                          onClick={() => setEditCatIcon(opt.name)}
                          className={`p-2 rounded-lg flex items-center justify-center transition-all ${editCatIcon === opt.name ? 'bg-slate-900 text-white' : 'hover:bg-slate-200 text-slate-500'}`}
                        >
                          <opt.icon className="h-4 w-4" />
                        </button>
                      ))}
                    </div>
                  </div>
                </div>

                <div className="grid gap-2">
                  <Label className="text-xs font-bold uppercase tracking-wider text-slate-500">Couleur</Label>
                  <div className="flex flex-wrap gap-2 p-3 bg-slate-50 rounded-xl border border-slate-200">
                    {COLOR_OPTIONS.map((opt) => (
                      <button
                        key={opt.name}
                        type="button"
                        onClick={() => setEditCatColor(opt.value)}
                        className={`h-8 w-8 rounded-full border-4 transition-all ${editCatColor === opt.value ? 'border-slate-300 scale-110' : 'border-transparent hover:scale-105'}`}
                        style={{ backgroundColor: opt.value }}
                        title={opt.name}
                      />
                    ))}
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="grid gap-2">
                    <Label htmlFor="edit-monthly-limit" className="text-xs font-bold uppercase tracking-wider text-slate-500">Limite mensuelle (€)</Label>
                    <Input
                      id="edit-monthly-limit"
                      type="number"
                      min="0"
                      placeholder="Ex: 200"
                      value={editMonthlyLimit}
                      onChange={(e) => setEditMonthlyLimit(e.target.value)}
                      className="bg-slate-50 border-slate-200"
                    />
                  </div>
                  <div className="grid gap-2">
                    <Label htmlFor="edit-annual-limit" className="text-xs font-bold uppercase tracking-wider text-slate-500">Limite annuelle (€)</Label>
                    <Input
                      id="edit-annual-limit"
                      type="number"
                      min="0"
                      placeholder="Ex: 2400"
                      value={editAnnualLimit}
                      onChange={(e) => setEditAnnualLimit(e.target.value)}
                      className="bg-slate-50 border-slate-200"
                    />
                  </div>
                </div>

                <div className="flex items-center gap-4 p-4 bg-slate-900 rounded-2xl text-white">
                  <div className="h-10 w-10 rounded-xl flex items-center justify-center" style={{ backgroundColor: editCatColor }}>
                    <IconComponent name={editCatIcon} className="h-6 w-6 text-white" />
                  </div>
                  <div>
                    <p className="text-sm font-bold">{editCatName || "Nom de la catégorie"}</p>
                    <p className="text-[10px] uppercase font-black opacity-50 tracking-widest">{editCatType}</p>
                  </div>
                </div>
              </div>
              <DialogFooter>
                <Button variant="ghost" onClick={() => setEditOpen(false)}>Annuler</Button>
                <Button onClick={handleUpdateCategory} className="bg-slate-900 text-white shadow-lg">Enregistrer les modifications</Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </TabsContent>

        <TabsContent value="tags" className="space-y-6">
          <TagsTab />
        </TabsContent>

        <TabsContent value="rules" className="space-y-6">
          <RulesTab />
        </TabsContent>

        <TabsContent value="transferts" className="space-y-6">
          <TransfersTab />
        </TabsContent>

        <TabsContent value="import" className="space-y-6">

          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <h2 className="text-2xl font-bold text-slate-900">Importation de données</h2>
          </div>
          <ImportTab />
        </TabsContent>

        <TabsContent value="system" className="space-y-8">
          <div className="grid gap-8 grid-cols-1 lg:grid-cols-2">
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
                        className="h-7 text-[10px] uppercase font-bold px-2"
                        onClick={() => setSelectedAccounts(accounts.map(a => a.id))}
                      >
                        Tout sélectionner
                      </Button>
                      <Button 
                        variant="ghost" 
                        size="sm" 
                        className="h-7 text-[10px] uppercase font-bold px-2"
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
                        className="flex items-center space-x-3 p-3 border rounded-xl bg-white hover:bg-slate-50 transition-colors"
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

            <Card className="shadow-sm border-rose-100 overflow-hidden">
              <CardHeader className="bg-rose-50/50 border-b border-rose-100">
                <div className="flex items-center gap-2 text-rose-600">
                  <AlertTriangle className="h-5 w-5" />
                  <CardTitle className="text-lg">Zone de danger</CardTitle>
                </div>
                <CardDescription className="text-rose-600/70">Ces actions sont irréversibles.</CardDescription>
              </CardHeader>
              <CardContent className="p-4 sm:p-6">
                <div className="flex flex-col gap-4">
                  <div className="p-4 sm:p-6 border border-rose-200 rounded-2xl bg-white space-y-4">
                    <div>
                      <p className="font-bold text-slate-900">Réinitialiser la base de données</p>
                      <p className="text-sm text-slate-500">Supprime tous les comptes, transactions et catégories personnalisées.</p>
                    </div>

                    <Dialog open={resetOpen} onOpenChange={setResetOpen}>
                      <DialogTrigger asChild>
                        <Button
                          variant="destructive"
                          className="w-full bg-rose-600 hover:bg-rose-700 shadow-lg shadow-rose-200"
                        >
                          <Database className="h-4 w-4 mr-2" /> Tout effacer définitivement
                        </Button>
                      </DialogTrigger>
                      <DialogContent className="sm:max-w-[425px]">
                        <DialogHeader>
                          <DialogTitle className="text-2xl font-bold text-rose-600 flex items-center gap-2">
                            <AlertTriangle className="h-6 w-6" /> Attention
                          </DialogTitle>
                          <DialogDescription className="text-slate-900 font-medium pt-2">
                            Cette action est irréversible. Vous perdrez TOUTES vos données (comptes, transactions, catégories).
                          </DialogDescription>
                        </DialogHeader>
                        <div className="py-6 space-y-4">
                          <p className="text-sm text-slate-500">
                            Pour confirmer la suppression, veuillez taper <span className="font-black text-rose-600 select-all">EFFACER</span> ci-dessous :
                          </p>
                          <Input 
                            value={resetConfirmText}
                            onChange={(e) => setResetConfirmText(e.target.value)}
                            placeholder="Tapez EFFACER ici..."
                            className="bg-rose-50 border-rose-200 focus-visible:ring-rose-500 font-bold text-center"
                          />
                        </div>
                        <DialogFooter>
                          <Button variant="ghost" onClick={() => { setResetOpen(false); setResetConfirmText(""); }}>Annuler</Button>
                          <Button
                            variant="destructive"
                            disabled={resetConfirmText !== "EFFACER"}
                            onClick={async () => {
                              try {
                                await api.post("/admin/reset-database", { 
                                  confirm: true,
                                  confirmation_code: resetConfirmText
                                })
                                toast.success("Base réinitialisée avec succès")
                                window.location.reload()
                              } catch (error) {
                                toast.error("Erreur lors de la réinitialisation")
                              }
                            }}
                          >
                            Confirmer la suppression totale
                          </Button>
                        </DialogFooter>
                      </DialogContent>
                    </Dialog>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  )
}
