import { Link } from "react-router-dom"
import type { PortfolioHolding } from "@/types/diversity"

interface HoldingNameProps {
  holding: PortfolioHolding
  className: string
  /** Classes du lien seulement (ex. hauteur tactile sur mobile) */
  linkClassName?: string
}

/** Nom d'une position ; un fonds (règle `is_etf` du backend) rattaché à un profil mène à sa fiche. */
export function HoldingName({ holding, className, linkClassName = "" }: HoldingNameProps) {
  const name = holding.asset_name || holding.ticker
  if (!holding.is_etf || !holding.etf_profile_id) return <span className={className} title={name}>{name}</span>
  return (
    <Link to={`/investments/etf/${holding.etf_profile_id}`} title={name}
      className={`${className} ${linkClassName} underline decoration-slate-300 underline-offset-2 hover:decoration-slate-900`}>
      {name}
    </Link>
  )
}
