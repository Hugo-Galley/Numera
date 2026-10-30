import * as accounts from "./accounts"
import { BODY, describeApiCases } from "@/test/apiCases"

describeApiCases("accounts", accounts, [
  { fn: "getAccounts", method: "GET", path: "/accounts" },
  { fn: "postAccounts", args: [BODY], method: "POST", path: "/accounts", body: BODY },
  { fn: "deleteAccountsById", args: [7], method: "DELETE", path: "/accounts/7" },
  { fn: "getAccountsById", args: [7], method: "GET", path: "/accounts/7" },
  { fn: "patchAccountsById", args: [7, BODY], method: "PATCH", path: "/accounts/7", body: BODY },
  { fn: "postBalanceSnapshots", args: [BODY], method: "POST", path: "/balance-snapshots", body: BODY },
  { fn: "postBalanceSnapshotsSetZeroPoint", args: [BODY], method: "POST", path: "/balance-snapshots/set-zero-point", body: BODY },
  { fn: "deleteBalanceSnapshotsById", args: [7], method: "DELETE", path: "/balance-snapshots/7" },
  { fn: "patchBalanceSnapshotsById", args: [7, BODY], method: "PATCH", path: "/balance-snapshots/7", body: BODY },
  { fn: "getLoansByAccountById", args: [7], method: "GET", path: "/loans/by-account/7" },
])
