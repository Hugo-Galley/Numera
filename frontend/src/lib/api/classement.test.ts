import * as classement from "./classement"
import { BODY, describeApiCases } from "@/test/apiCases"

describeApiCases("classement", classement, [
  { fn: "getCategories", args: ["?include_archived=true"], method: "GET", path: "/categories", query: "?include_archived=true" },
  { fn: "postCategories", args: [BODY], method: "POST", path: "/categories", body: BODY },
  { fn: "deleteCategoriesById", args: [7], method: "DELETE", path: "/categories/7" },
  { fn: "patchCategoriesById", args: [7, BODY], method: "PATCH", path: "/categories/7", body: BODY },
  { fn: "postCategorizationRules", args: [BODY], method: "POST", path: "/categorization-rules", body: BODY },
  { fn: "getMerchants", method: "GET", path: "/merchants" },
  { fn: "postMerchants", args: [BODY], method: "POST", path: "/merchants", body: BODY },
  { fn: "deleteMerchantsAliasesById", args: [7], method: "DELETE", path: "/merchants/aliases/7" },
  { fn: "postMerchantsAutoNormalize", method: "POST", path: "/merchants/auto-normalize" },
  { fn: "getMerchantsSuggestionsUnnormalized", args: ["?limit=20"], method: "GET", path: "/merchants/suggestions/unnormalized", query: "?limit=20" },
  { fn: "deleteMerchantsById", args: [7], method: "DELETE", path: "/merchants/7" },
  { fn: "getMerchantsById", args: [7], method: "GET", path: "/merchants/7" },
  { fn: "putMerchantsById", args: [7, BODY], method: "PUT", path: "/merchants/7", body: BODY },
  { fn: "postMerchantsAliases", args: [7, BODY], method: "POST", path: "/merchants/7/aliases", body: BODY },
  { fn: "getTags", method: "GET", path: "/tags" },
])
