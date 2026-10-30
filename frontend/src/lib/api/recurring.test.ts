import * as recurring from "./recurring"
import { BODY, describeApiCases } from "@/test/apiCases"

describeApiCases("recurring", recurring, [
  { fn: "getRecurringTransactions", method: "GET", path: "/recurring-transactions/" },
  { fn: "postRecurringTransactions", args: [BODY], method: "POST", path: "/recurring-transactions/", body: BODY },
  { fn: "postRecurringTransactionsTrigger", method: "POST", path: "/recurring-transactions/trigger" },
  { fn: "deleteRecurringTransactionsById", args: [7], method: "DELETE", path: "/recurring-transactions/7" },
  { fn: "patchRecurringTransactionsById", args: [7, BODY], method: "PATCH", path: "/recurring-transactions/7", body: BODY },
  { fn: "getSalaryConfig", method: "GET", path: "/salary/config" },
  { fn: "postSalaryConfig", args: [BODY], method: "POST", path: "/salary/config", body: BODY },
  { fn: "putSalaryConfig", args: [BODY], method: "PUT", path: "/salary/config", body: BODY },
  { fn: "deleteSalaryGenerateById", args: [2026, 6], method: "DELETE", path: "/salary/generate/2026/6" },
  { fn: "postSalaryGenerateById", args: [2026, 6], method: "POST", path: "/salary/generate/2026/6" },
  { fn: "putSalaryMonthsById", args: [2026, 6, BODY], method: "PUT", path: "/salary/months/2026/6", body: BODY },
  { fn: "getSalarySummaryById", args: [2026, 6], method: "GET", path: "/salary/summary/2026/6" },
  { fn: "getSalaryTelecommutingById", args: [2026, 6], method: "GET", path: "/salary/telecommuting/2026/6" },
  { fn: "putSalaryTelecommutingById", args: [2026, 6, BODY], method: "PUT", path: "/salary/telecommuting/2026/6", body: BODY },
])
