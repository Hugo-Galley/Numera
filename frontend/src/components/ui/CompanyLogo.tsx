import React, { useState, useEffect } from "react"

const NAME_TO_TICKER: Record<string, string> = {
  apple: "AAPL",
  microsoft: "MSFT",
  nvidia: "NVDA",
  amazon: "AMZN",
  alphabet: "GOOGL",
  google: "GOOGL",
  meta: "META",
  tesla: "TSLA",
  broadcom: "AVGO",
  tsmc: "TSM",
  taiwan: "TSM",
  asml: "ASML",
  "eli lilly": "LLY",
  berkshire: "BRK-B",
  jpmorgan: "JPM",
  "novo nordisk": "NOVO-B.CO",
  lvmh: "MC.PA",
  totalenergies: "TTE.PA",
  total: "TTE.PA",
  sanofi: "SAN.PA",
  schneider: "SU.PA",
  "air liquide": "AI.PA",
  bnp: "BNP.PA",
  axa: "CS.PA",
  hermes: "RMS.PA",
  "hermès": "RMS.PA",
  "l'oreal": "OR.PA",
  "l'oréal": "OR.PA",
  vinci: "DG.PA",
  danone: "BN.PA",
  safran: "SAF.PA",
  kering: "KER.PA",
  stellantis: "STLAP.PA",
  essilorluxottica: "EL.PA",
  capgemini: "CAP.PA",
  "pernod ricard": "RI.PA",
  "saint-gobain": "SGO.PA",
  engie: "ENGI.PA",
  "credit agricole": "ACA.PA",
  "crédit agricole": "ACA.PA",
  "societe generale": "GLE.PA",
  "société générale": "GLE.PA",
  orange: "ORA.PA",
  michelin: "ML.PA",
  carrefour: "CA.PA",
  veolia: "VIE.PA",
  legrand: "LR.PA",
  publicis: "PUB.PA",
  sap: "SAP",
  siemens: "SIE.DE",
  allianz: "ALV.DE",
  nestle: "NESN.SW",
  "nestlé": "NESN.SW",
  roche: "ROG.SW",
  novartis: "NOVN.SW",
  astrazeneca: "AZN.L",
  shell: "SHEL.L",
  toyota: "TM",
  samsung: "005930.KS",
  alibaba: "BABA",
  tencent: "0700.HK",
}

function resolveSymbol(ticker?: string, name?: string): string[] {
  const candidates: string[] = []

  if (ticker) {
    const cleanT = ticker.trim().toUpperCase()
    candidates.push(cleanT)
    if (cleanT.includes(".")) {
      candidates.push(cleanT.split(".")[0])
    }
  }

  if (name) {
    const lower = name.toLowerCase()
    for (const [key, sym] of Object.entries(NAME_TO_TICKER)) {
      if (lower.includes(key)) {
        if (!candidates.includes(sym)) {
          candidates.push(sym)
        }
        if (sym.includes(".")) {
          const base = sym.split(".")[0]
          if (!candidates.includes(base)) {
            candidates.push(base)
          }
        }
      }
    }
  }

  return candidates
}

function getInitials(name?: string, ticker?: string): string {
  if (ticker && ticker.length <= 4 && !ticker.includes(".")) {
    return ticker.slice(0, 3)
  }
  if (name) {
    const parts = name.trim().split(/\s+/)
    if (parts.length >= 2) {
      return (parts[0][0] + parts[1][0]).toUpperCase()
    }
    return name.slice(0, 2).toUpperCase()
  }
  if (ticker) {
    return ticker.slice(0, 2).toUpperCase()
  }
  return "•"
}

interface CompanyLogoProps {
  ticker?: string
  name?: string
  className?: string
  alt?: string
}

export function CompanyLogo({ ticker, name, className = "h-7 w-7", alt }: CompanyLogoProps) {
  const candidates = resolveSymbol(ticker, name)
  const [candidateIndex, setCandidateIndex] = useState(0)
  const [hasError, setHasError] = useState(false)

  // Reset state if ticker or name changes
  useEffect(() => {
    setCandidateIndex(0)
    setHasError(candidates.length === 0)
  }, [ticker, name])

  const currentSymbol = candidates[candidateIndex]

  if (hasError || !currentSymbol) {
    const initials = getInitials(name, ticker)
    return (
      <div
        className={`flex items-center justify-center font-bold text-[10px] tracking-tight bg-slate-100 text-slate-700 rounded-md border border-slate-200 select-none shrink-0 ${className}`}
        title={name || ticker}
      >
        {initials}
      </div>
    )
  }

  const logoUrl = `https://assets.parqet.com/logos/symbol/${encodeURIComponent(currentSymbol)}`

  return (
    <div className={`relative flex items-center justify-center rounded-md overflow-hidden bg-white border border-slate-100 shrink-0 ${className}`}>
      <img
        src={logoUrl}
        alt={alt || name || ticker || "Company logo"}
        className="w-full h-full object-contain p-0.5"
        loading="lazy"
        onError={() => {
          if (candidateIndex + 1 < candidates.length) {
            setCandidateIndex(candidateIndex + 1)
          } else {
            setHasError(true)
          }
        }}
      />
    </div>
  )
}
