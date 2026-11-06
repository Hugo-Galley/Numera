import type { resources } from "./index"

// Clés de traduction typées : une faute de frappe dans `t("…")` fait échouer `tsc`
declare module "i18next" {
  interface CustomTypeOptions {
    defaultNS: "common"
    resources: (typeof resources)["fr"]
  }
}
