import * as savings from "./savings"
import { BODY, describeApiCases } from "@/test/apiCases"

describeApiCases("savings", savings, [
  { fn: "getGoals", method: "GET", path: "/goals" },
  { fn: "postGoals", args: [BODY], method: "POST", path: "/goals", body: BODY },
  { fn: "deleteGoalsById", args: [7], method: "DELETE", path: "/goals/7" },
  { fn: "patchGoalsById", args: [7, BODY], method: "PATCH", path: "/goals/7", body: BODY },
  { fn: "getProvisions", method: "GET", path: "/provisions" },
  { fn: "postProvisions", args: [BODY], method: "POST", path: "/provisions", body: BODY },
  { fn: "getProvisionsSummary", method: "GET", path: "/provisions/summary" },
  { fn: "deleteProvisionsById", args: [7], method: "DELETE", path: "/provisions/7" },
  { fn: "patchProvisionsById", args: [7, BODY], method: "PATCH", path: "/provisions/7", body: BODY },
])
