import { nowLocalInput, todayLocal } from "@/lib/dates"
import { useState } from "react"
import type { useAccountDetailState } from "./useAccountDetailState"

/** État des formulaires (transaction, snapshot, flux d'investissement, point zéro). */
export function useAccountForms(p: ReturnType<typeof useAccountDetailState>) {
  const [txOpen, setTxOpen] = useState(false)
  const [editTxId, setEditTxId] = useState<number | null>(null)
  const [txDate, setTxDate] = useState(() => nowLocalInput())
  const [txType, setTxType] = useState("Sortie")
  const [txMerchant, setTxMerchant] = useState("")
  const [txAmount, setTxAmount] = useState("")
  const [txCurrency, setTxCurrency] = useState("EUR")
  const [txCategoryId, setTxCategoryId] = useState<string>("none")
  const [txTagIds, setTxTagIds] = useState<number[]>([])
  const [txNote, setTxNote] = useState("")
  const [txIsRecurring, setTxIsRecurring] = useState(false)
  const [txIsExceptional, setTxIsExceptional] = useState(false)
  const [txCustomIcon, setTxCustomIcon] = useState("")
  const [txCustomColor, setTxCustomColor] = useState("#0f172a")

  // -- Snapshot Form State --
  const [snapOpen, setSnapOpen] = useState(false)
  const [editSnapId, setEditSnapId] = useState<number | null>(null)
  const [snapDate, setSnapDate] = useState(() => todayLocal())
  const [snapValue, setSnapValue] = useState("")
  const [snapNote, setSnapNote] = useState("")

  // -- Investment Flux Form State --
  const [invTxOpen, setInvTxOpen] = useState(false)
  const [editInvTxId, setEditInvTxId] = useState<number | null>(null)
  const [invTxDate, setInvTxDate] = useState(() => nowLocalInput())
  const [invTxType, setInvTxType] = useState<"versement" | "retrait" | "dividende" | "achat" | "vente" | "frais">("versement")
  const [invTxAmount, setInvTxAmount] = useState("")
  const [invTxCurrency, setInvTxCurrency] = useState("EUR")
  const [invTxNote, setInvTxNote] = useState("")
  const [invTxTicker, setInvTxTicker] = useState("")
  const [invTxIsin, setInvTxIsin] = useState("")
  const [invTxQuantity, setInvTxQuantity] = useState("")
  const [invTxUnitPrice, setInvTxUnitPrice] = useState("")
  const [invTxFees, setInvTxFees] = useState("")
  const [invTxWithholding, setInvTxWithholding] = useState("")
  const [invTxReinvested, setInvTxReinvested] = useState(false)
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
  const [zeroDate, setZeroDate] = useState(() => todayLocal())
  const [zeroValue, setZeroValue] = useState("")
  const [zeroNote, setZeroNote] = useState("")
  return { txOpen, setTxOpen, editTxId, setEditTxId, txDate, setTxDate, txType, setTxType, txMerchant, setTxMerchant, txAmount, setTxAmount, txCurrency, setTxCurrency, txCategoryId, setTxCategoryId, txTagIds, setTxTagIds, txNote, setTxNote, txIsRecurring, setTxIsRecurring, txIsExceptional, setTxIsExceptional, txCustomIcon, setTxCustomIcon, txCustomColor, setTxCustomColor, snapOpen, setSnapOpen, editSnapId, setEditSnapId, snapDate, setSnapDate, snapValue, setSnapValue, snapNote, setSnapNote, invTxOpen, setInvTxOpen, editInvTxId, setEditInvTxId, invTxDate, setInvTxDate, invTxType, setInvTxType, invTxAmount, setInvTxAmount, invTxCurrency, setInvTxCurrency, invTxNote, setInvTxNote, invTxTicker, setInvTxTicker, invTxIsin, setInvTxIsin, invTxQuantity, setInvTxQuantity, invTxUnitPrice, setInvTxUnitPrice, invTxFees, setInvTxFees, invTxWithholding, setInvTxWithholding, invTxReinvested, setInvTxReinvested, invTxAssetClass, setInvTxAssetClass, invTxSector, setInvTxSector, invTxZone, setInvTxZone, suggestions, setSuggestions, zeroOpen, setZeroOpen, zeroDate, setZeroDate, zeroValue, setZeroValue, zeroNote, setZeroNote }
}
