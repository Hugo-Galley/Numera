import React, { useState, useEffect, useMemo } from "react"

const NAME_TO_TICKER: Record<string, string> = {
  // Tech & Global
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
  cisco: "CSCO",
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

  // CAC 40 & French Large Caps
  lvmh: "MC.PA",
  totalenergies: "TTE.PA",
  total: "TTE.PA",
  sanofi: "SAN.PA",
  schneider: "SU.PA",
  "air liquide": "AI.PA",
  bnp: "BNP.PA",
  axa: "CS.PA",
  thales: "HO.PA",
  airbus: "AIR.PA",
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
  renault: "RNO.PA",
}

// Major ETF issuers and funds mapping
const ISSUER_PATTERNS: Array<{
  keywords: string[]
  urls: string[]
}> = [
  {
    // iShares / BlackRock (WPEA, EUNL, etc.)
    keywords: ["ishare", "ishares", "wpea"],
    urls: [
      "https://assets.parqet.com/logos/symbol/EUNL.DE",
      "https://assets.parqet.com/logos/symbol/BLK",
    ],
  },
  {
    // AXA Investment Managers / AXA funds
    keywords: ["axa", "0p0001hi7f"],
    urls: [
      "https://assets.parqet.com/logos/symbol/CS.PA",
      "https://www.google.com/s2/favicons?domain=axa.fr&sz=128",
    ],
  },
  {
    // Amundi / Lyxor / AIS (Amundi Index Solutions)
    keywords: ["amundi", "lyxor", "ais-", "ais ", "ahyq", "cw8", "panx", "c40", "meud", "paeem"],
    urls: [
      "https://assets.parqet.com/logos/symbol/AMUN.PA",
      "https://assets.parqet.com/logos/symbol/CW8.PA",
    ],
  },
  {
    // BNP Paribas / EasyETF / Parvest
    keywords: ["bnp", "easyetf", "parvest", "ese"],
    urls: [
      "https://assets.parqet.com/logos/symbol/BNP.PA",
      "https://assets.parqet.com/logos/symbol/ESE.PA",
    ],
  },
  {
    // Vanguard
    keywords: ["vanguard"],
    urls: [
      "https://assets.parqet.com/logos/symbol/VOO",
      "https://assets.parqet.com/logos/symbol/VTI",
    ],
  },
  {
    // DWS / Xtrackers
    keywords: ["xtrackers", "xtracker", "dws"],
    urls: [
      "https://assets.parqet.com/logos/symbol/DWS.DE",
    ],
  },
  {
    // State Street / SPDR
    keywords: ["spdr", "state street"],
    urls: [
      "https://assets.parqet.com/logos/symbol/STT",
    ],
  },
  {
    // Invesco
    keywords: ["invesco"],
    urls: [
      "https://assets.parqet.com/logos/symbol/IVZ",
    ],
  },
  {
    // Carmignac
    keywords: ["carmignac", "0p00000g01", "0p00000g02"],
    urls: [
      "https://www.google.com/s2/favicons?domain=carmignac.com&sz=128",
    ],
  },
  {
    // Comgest
    keywords: ["comgest", "0p00000k6a"],
    urls: [
      "https://www.google.com/s2/favicons?domain=comgest.com&sz=128",
    ],
  },
  {
    // BlackRock
    keywords: ["blackrock"],
    urls: [
      "https://assets.parqet.com/logos/symbol/BLK",
    ],
  },
]

function resolveCandidates(ticker?: string, name?: string, isin?: string): string[] {
  const candidates: string[] = []
  const textCombined = `${ticker || ""} ${name || ""}`.toLowerCase()

  // 1. Check known issuer & fund patterns first (e.g. iShares, AXA, Amundi, etc.)
  for (const group of ISSUER_PATTERNS) {
    if (group.keywords.some((k) => textCombined.includes(k))) {
      for (const u of group.urls) {
        if (!candidates.includes(u)) {
          candidates.push(u)
        }
      }
    }
  }

  // 2. ISIN candidate (if provided and valid format)
  const cleanIsin = (isin || (ticker && /^[A-Z]{2}[A-Z0-9]{10}$/i.test(ticker.trim()) ? ticker : ""))
    .trim()
    .toUpperCase()
  if (cleanIsin && cleanIsin.length === 12) {
    const isinUrl = `https://assets.parqet.com/logos/isin/${cleanIsin}`
    if (!candidates.includes(isinUrl)) {
      candidates.push(isinUrl)
    }
  }

  // 3. Ticker candidates (if ticker is not an obscure Morningstar code)
  if (ticker) {
    const cleanT = ticker.trim().toUpperCase()
    if (!cleanT.startsWith("0P")) {
      const symUrl1 = `https://assets.parqet.com/logos/symbol/${encodeURIComponent(cleanT)}`
      if (!candidates.includes(symUrl1)) {
        candidates.push(symUrl1)
      }
      if (cleanT.includes(".")) {
        const base = cleanT.split(".")[0]
        const symUrl2 = `https://assets.parqet.com/logos/symbol/${encodeURIComponent(base)}`
        if (!candidates.includes(symUrl2)) {
          candidates.push(symUrl2)
        }
      }
    }
  }

  // 4. Name to Ticker mapping (stocks & companies)
  for (const [key, sym] of Object.entries(NAME_TO_TICKER)) {
    if (textCombined.includes(key)) {
      const symUrl = `https://assets.parqet.com/logos/symbol/${encodeURIComponent(sym)}`
      if (!candidates.includes(symUrl)) {
        candidates.push(symUrl)
      }
    }
  }

  return candidates
}

function getInitials(name?: string, ticker?: string): string {
  if (ticker && ticker.length <= 4 && !ticker.includes(".")) {
    return ticker.slice(0, 3).toUpperCase()
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
  isin?: string
  className?: string
  alt?: string
}

export function CompanyLogo({ ticker, name, isin, className = "h-7 w-7", alt }: CompanyLogoProps) {
  const candidates = useMemo(() => resolveCandidates(ticker, name, isin), [ticker, name, isin])
  const [candidateIndex, setCandidateIndex] = useState(0)
  const [hasError, setHasError] = useState(false)

  // Reset state if candidates change
  useEffect(() => {
    setCandidateIndex(0)
    setHasError(candidates.length === 0)
  }, [candidates])

  const currentUrl = candidates[candidateIndex]

  if (hasError || !currentUrl) {
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

  return (
    <div className={`relative flex items-center justify-center rounded-md overflow-hidden bg-white border border-slate-100 shrink-0 ${className}`}>
      <img
        key={currentUrl}
        src={currentUrl}
        alt={alt || name || ticker || "Company logo"}
        className="w-full h-full object-contain p-0.5"
        onError={() => {
          if (candidateIndex + 1 < candidates.length) {
            setCandidateIndex((prev) => prev + 1)
          } else {
            setHasError(true)
          }
        }}
      />
    </div>
  )
}
