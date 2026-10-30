import * as investments from "./investments"
import { BODY, describeApiCases } from "@/test/apiCases"

describeApiCases("investments", investments, [
  { fn: "postEtfProfilesAutoDecompose", args: [BODY], method: "POST", path: "/etf-profiles/auto-decompose", body: BODY },
  { fn: "postEtfProfilesRefreshHeld", method: "POST", path: "/etf-profiles/refresh-held" },
  { fn: "getHoldings", args: ["?account_id=7"], method: "GET", path: "/holdings", query: "?account_id=7" },
  { fn: "postHoldingsBaseline", args: [BODY], method: "POST", path: "/holdings/baseline", body: BODY },
  { fn: "getHoldingsSuggestions", args: ["?account_id=7"], method: "GET", path: "/holdings/suggestions", query: "?account_id=7" },
  { fn: "deleteHoldingsById", args: [7], method: "DELETE", path: "/holdings/7" },
  { fn: "putHoldingsById", args: [7, BODY], method: "PUT", path: "/holdings/7", body: BODY },
  { fn: "postInvestmentTransactions", args: [BODY], method: "POST", path: "/investment-transactions", body: BODY },
  { fn: "deleteInvestmentTransactionsById", args: [7], method: "DELETE", path: "/investment-transactions/7" },
  { fn: "patchInvestmentTransactionsById", args: [7, BODY], method: "PATCH", path: "/investment-transactions/7", body: BODY },
  { fn: "getMarketQuote", args: ["?symbol=CW8.PA"], method: "GET", path: "/market/quote", query: "?symbol=CW8.PA" },
  { fn: "getMarketSearch", args: ["?q=msci"], method: "GET", path: "/market/search", query: "?q=msci" },
  { fn: "getTaxAnnualReport", args: ["?year=2026"], method: "GET", path: "/tax/annual-report", query: "?year=2026" },
  { fn: "getTaxOverview", method: "GET", path: "/tax/overview" },
  { fn: "patchTaxSettings", args: [BODY], method: "PATCH", path: "/tax/settings", body: BODY },
])
