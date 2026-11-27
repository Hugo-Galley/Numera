import { Link } from "react-router-dom"
import type { PortfolioHolding } from "@/types/diversity"

/** Nom d'une position ; un fonds rattaché à un profil mène à sa fiche. */
export function HoldingName({ holding, className }: { holding: PortfolioHolding; className: string }) {
  const name = holding.asset_name || holding.ticker
  if (!holding.etf_profile_id) return <span className={className} title={name}>{name}</span>
  return (
    <Link to={`/investments/etf/${holding.etf_profile_id}`} title={name}
      className={`${className} underline decoration-slate-300 underline-offset-2 hover:decoration-slate-900`}>
      {name}
    </Link>
  )
}
