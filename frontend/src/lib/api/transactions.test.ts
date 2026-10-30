import * as transactions from "./transactions"
import { BODY, describeApiCases } from "@/test/apiCases"

const form = () => {
  const data = new FormData()
  data.append("file", new Blob(["date;montant\n"], { type: "text/csv" }), "releve.csv")
  return data
}

describeApiCases("transactions", transactions, [
  { fn: "uploadImportCommit", args: [form()], method: "POST", path: "/import/commit", upload: true },
  { fn: "uploadImportPreview", args: [form()], method: "POST", path: "/import/preview", upload: true },
  { fn: "getTransactions", args: ["?account_id=7&limit=50"], method: "GET", path: "/transactions", query: "?account_id=7&limit=50" },
  { fn: "postTransactions", args: [BODY], method: "POST", path: "/transactions", body: BODY },
  { fn: "patchTransactionsBulk", args: [BODY], method: "PATCH", path: "/transactions/bulk", body: BODY },
  { fn: "postTransactionsBulkDelete", args: [{ ids: [1, 2] }], method: "POST", path: "/transactions/bulk-delete", body: { ids: [1, 2] } },
  { fn: "getTransactionsMerchants", method: "GET", path: "/transactions/merchants" },
  { fn: "deleteTransactionsById", args: [7], method: "DELETE", path: "/transactions/7" },
  { fn: "patchTransactionsById", args: [7, BODY], method: "PATCH", path: "/transactions/7", body: BODY },
  { fn: "postTransactionsIgnore", args: [7], method: "POST", path: "/transactions/7/ignore" },
  { fn: "postTransactionsIgnoreDuplicate", args: [7], method: "POST", path: "/transactions/7/ignore-duplicate" },
  { fn: "postTransactionsLinkById", args: [7, 8, "?kind=transfer", BODY], method: "POST", path: "/transactions/7/link/8", query: "?kind=transfer", body: BODY },
])
