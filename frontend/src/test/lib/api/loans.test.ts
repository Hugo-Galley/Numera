import * as loans from "@/lib/api/loans"
import { BODY, describeApiCases } from "@/test/support/apiCases"

describeApiCases("loans", loans, [
  { fn: "patchLoansById", args: [7, BODY], method: "PATCH", path: "/loans/7", body: BODY },
  { fn: "postLoans", args: [BODY], method: "POST", path: "/loans", body: BODY },
  { fn: "getLoansSchedule", args: [7], method: "GET", path: "/loans/7/schedule" },
  { fn: "postLoansSimulatePrepayment", args: [7, BODY], method: "POST", path: "/loans/7/simulate-prepayment", body: BODY },
  { fn: "postLoansPrepayments", args: [7, BODY], method: "POST", path: "/loans/7/prepayments", body: BODY },
  { fn: "deleteLoansPrepaymentsById", args: [7, 8], method: "DELETE", path: "/loans/7/prepayments/8" },
  { fn: "deleteLoansById", args: [7], method: "DELETE", path: "/loans/7" },
])
