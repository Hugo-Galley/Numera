import { useEffect, useState } from "react"
import { api } from "@/lib/api"
import { CompanyLogo } from "@/components/ui/CompanyLogo"

type AccountBrand = { id: number; name: string; institution?: string | null; logo?: string | null }

// Cache partagé : un seul GET /accounts pour tous les <AccountLogo> de l'écran.
let brands: Map<number, AccountBrand> | null = null
let loading: Promise<void> | null = null
const listeners = new Set<() => void>()

function load() {
  if (loading) return
  loading = api
    .get<AccountBrand[]>("/accounts")
    .then((list) => {
      brands = new Map(list.map((a) => [a.id, a]))
    })
    .catch(() => {
      brands = new Map()
    })
    .finally(() => {
      loading = null
      listeners.forEach((fn) => fn())
    })
}

/** À appeler après création/modification d'un compte pour rafraîchir les logos affichés. */
export function invalidateAccountLogos() {
  brands = null
  load()
}

interface AccountLogoProps {
  accountId: number | null | undefined
  /** Logo déjà connu (évite d'attendre le cache, ex. liste de comptes déjà chargée). */
  logo?: string | null
  className?: string
}

export function AccountLogo({ accountId, logo, className = "h-6 w-6" }: AccountLogoProps) {
  const [, rerender] = useState(0)

  useEffect(() => {
    const fn = () => rerender((n) => n + 1)
    listeners.add(fn)
    if (!brands) load()
    return () => {
      listeners.delete(fn)
    }
  }, [])

  const brand = accountId != null ? brands?.get(accountId) : undefined
  const ref = logo !== undefined ? logo : brand?.logo
  if (!ref) return null
  return <CompanyLogo logo={ref} name={brand?.institution || brand?.name} className={className} />
}
