import * as monthReview from "@/lib/api/monthReview"
import { BODY, describeApiCases } from "@/test/support/apiCases"

describeApiCases("monthReview", monthReview, [
  { fn: "getMonthReviewClosures", method: "GET", path: "/month-review/closures" },
  { fn: "getMonthReview", args: ["?a=1"], method: "GET", path: "/month-review", query: "?a=1" },
  { fn: "postMonthReviewClose", args: [BODY], method: "POST", path: "/month-review/close", body: BODY },
  { fn: "deleteMonthReview", args: ["?a=1"], method: "DELETE", path: "/month-review", query: "?a=1" },
])
