import * as reimbursements from "@/lib/api/reimbursements"
import { BODY, describeApiCases } from "@/test/support/apiCases"

describeApiCases("reimbursements", reimbursements, [
  { fn: "getReimbursementsClaimsCandidates", args: [7], method: "GET", path: "/reimbursements/claims/7/candidates" },
  { fn: "postReimbursementsClaimsAllocations", args: [7, BODY], method: "POST", path: "/reimbursements/claims/7/allocations", body: BODY },
  { fn: "getReimbursementsClaims", args: ["?a=1"], method: "GET", path: "/reimbursements/claims", query: "?a=1" },
  { fn: "getReimbursementsEntriesClaims", args: [7], method: "GET", path: "/reimbursements/entries/7/claims" },
  { fn: "postReimbursementsClaims", args: [BODY], method: "POST", path: "/reimbursements/claims", body: BODY },
  { fn: "deleteReimbursementsClaimsById", args: [7], method: "DELETE", path: "/reimbursements/claims/7" },
  { fn: "patchReimbursementsClaimsById", args: [7, BODY], method: "PATCH", path: "/reimbursements/claims/7", body: BODY },
  { fn: "deleteReimbursementsAllocationsById", args: [7], method: "DELETE", path: "/reimbursements/allocations/7" },
  { fn: "getReimbursementsSummary", method: "GET", path: "/reimbursements/summary" },
])
