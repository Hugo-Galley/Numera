import { useState } from "react"
import { AlertCircle, CheckCircle2, ArrowRight, ChevronDown } from "lucide-react"
import { Button } from "@/components/ui/button"
import { api } from "@/lib/api"
import { useNavigate } from "react-router-dom"

interface Account {
  id: number
  name: string
  type: string
  last_verified_at: string
  active: boolean
}

export function AccountVerificationBanner({
  accounts,
  onAccountVerified
}: {
  accounts: Account[]
  onAccountVerified: () => void
}) {
  const navigate = useNavigate()
  const [verifying, setVerifying] = useState<number | null>(null)
  // Replié par défaut : la liste dépliée occupait la moitié du tableau de bord
  const [open, setOpen] = useState(false)

  const now = new Date()
  const daysDiff = (dateStr: string) => {
    const d = new Date(dateStr)
    const diffTime = Math.abs(now.getTime() - d.getTime())
    return Math.floor(diffTime / (1000 * 60 * 60 * 24))
  }

  const unverifiedAccounts = accounts.filter(
    a => a.active && daysDiff(a.last_verified_at) >= 15
  )

  if (unverifiedAccounts.length === 0) return null

  const handleVerify = async (id: number) => {
    try {
      setVerifying(id)
      await api.post(`/accounts/${id}/verify`)
      onAccountVerified()
    } catch (e) {
      console.error(e)
    } finally {
      setVerifying(null)
    }
  }

  return (
    <div className="bg-amber-50 border border-amber-200 text-amber-900 mb-0 md:mb-8 rounded-lg">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="flex w-full min-h-11 items-center gap-2 px-4 py-2.5 text-left text-sm"
      >
        <AlertCircle className="h-4 w-4 shrink-0 text-amber-600" />
        <span className="whitespace-nowrap font-semibold text-amber-800">
          {unverifiedAccounts.length} compte{unverifiedAccounts.length > 1 ? "s" : ""} à mettre à jour
        </span>
        <span className="hidden min-w-0 truncate text-amber-700 sm:inline">
          · {unverifiedAccounts.map((a) => a.name).join(", ")}
        </span>
        <ChevronDown className={`ml-auto h-4 w-4 shrink-0 text-amber-700 transition-transform ${open ? "rotate-180" : ""}`} />
      </button>
      {open && <div className="space-y-4 px-4 pb-4 text-sm">
        <p>Cela fait plus de 15 jours que vous n'avez pas mis à jour ces comptes. Veuillez vérifier s'il y a de nouvelles transactions ou valider leur solde.</p>
        
        <div className="grid gap-3 sm:grid-cols-2 md:grid-cols-3">
          {unverifiedAccounts.map(acc => (
            <div key={acc.id} className="bg-white/60 p-3 rounded-lg border border-amber-200/50 flex flex-col justify-between space-y-3">
              <div>
                <p className="font-medium text-amber-900">{acc.name}</p>
                <p className="text-xs text-amber-700 opacity-80">
                  Dernière maj: il y a {daysDiff(acc.last_verified_at)} jours
                </p>
              </div>
              
              <div className="flex items-center gap-2">
                {(acc.type === "investissement" || acc.type === "assurance_vie") ? (
                  <Button 
                    size="sm" 
                    variant="outline" 
                    className="w-full bg-white hover:bg-amber-100 hover:text-amber-900 border-amber-200 text-amber-800 h-10 md:h-8 text-xs"
                    onClick={() => navigate(`/accounts/${acc.id}`)}
                  >
                    Faire un snapshot
                    <ArrowRight className="ml-1.5 h-3 w-3" />
                  </Button>
                ) : (
                  <>
                    <Button 
                      size="sm" 
                      variant="outline" 
                      className="flex-1 bg-white hover:bg-amber-100 hover:text-amber-900 border-amber-200 text-amber-800 h-10 md:h-8 text-xs px-2"
                      onClick={() => handleVerify(acc.id)}
                      disabled={verifying === acc.id}
                    >
                      <CheckCircle2 className="mr-1.5 h-3 w-3" />
                      Rien n'a bougé
                    </Button>
                    <Button 
                      size="sm" 
                      variant="ghost" 
                      className="flex-1 hover:bg-amber-100 hover:text-amber-900 text-amber-800 h-10 md:h-8 text-xs px-2"
                      onClick={() => navigate(`/accounts/${acc.id}`)}
                    >
                      Aller au compte
                    </Button>
                  </>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>}
    </div>
  )
}
