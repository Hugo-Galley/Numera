/** Réglages, authentification (double facteur, passkeys), sauvegardes, accès MCP, notifications, logos. Une fonction par route ; `query` (« ?a=1&b=2 ») est ajouté tel quel à l'URL. */
import { api } from "@/lib/api"
import type { ApiBody, ApiResponse, Id } from "./types"

/** GET /admin/backup/status */
export const getAdminBackupStatus = <T = ApiResponse<"/admin/backup/status", "get">>() => api.get<T>(`/admin/backup/status`)

/** POST /admin/backup/run */
export const postAdminBackupRun = <T = ApiResponse<"/admin/backup/run", "post">>(body?: unknown) => api.post<T>(`/admin/backup/run`, body)

/** POST /admin/reset-database */
export const postAdminResetDatabase = <T = ApiResponse<"/admin/reset-database", "post">>(body?: ApiBody<"/admin/reset-database", "post">) => api.post<T>(`/admin/reset-database`, body)

/** PUT /admin/profile */
export const putAdminProfile = <T = ApiResponse<"/admin/profile", "put">>(body?: ApiBody<"/admin/profile", "put">) => api.put<T>(`/admin/profile`, body)

/** GET /import/logs */
export const getImportLogs = <T = ApiResponse<"/import/logs", "get">>() => api.get<T>(`/import/logs`)

/** GET /admin/login-events */
export const getAdminLoginEvents = <T = ApiResponse<"/admin/login-events", "get">>(query = "") => api.get<T>(`/admin/login-events${query}`)

/** POST /admin/logout-all */
export const postAdminLogoutAll = <T = ApiResponse<"/admin/logout-all", "post">>(body?: unknown) => api.post<T>(`/admin/logout-all`, body)

/** GET /admin/mcp-tokens */
export const getAdminMcpTokens = <T = ApiResponse<"/admin/mcp-tokens", "get">>() => api.get<T>(`/admin/mcp-tokens`)

/** POST /admin/mcp-tokens */
export const postAdminMcpTokens = <T = ApiResponse<"/admin/mcp-tokens", "post">>(body?: ApiBody<"/admin/mcp-tokens", "post">) => api.post<T>(`/admin/mcp-tokens`, body)

/** DELETE /admin/mcp-tokens/:id */
export const deleteAdminMcpTokensById = <T = void>(id: Id) => api.delete<T>(`/admin/mcp-tokens/${id}`)

/** GET /notifications/settings */
export const getNotificationsSettings = <T = ApiResponse<"/notifications/settings", "get">>() => api.get<T>(`/notifications/settings`)

/** PUT /notifications/settings */
export const putNotificationsSettings = <T = ApiResponse<"/notifications/settings", "put">>(body?: ApiBody<"/notifications/settings", "put">) => api.put<T>(`/notifications/settings`, body)

/** POST /notifications/test */
export const postNotificationsTest = <T = ApiResponse<"/notifications/test", "post">>(body?: ApiBody<"/notifications/test", "post">) => api.post<T>(`/notifications/test`, body)

/** GET /auth/passkey */
export const getAuthPasskey = <T = ApiResponse<"/auth/passkey", "get">>() => api.get<T>(`/auth/passkey`)

/** POST /auth/passkey/register/options */
export const postAuthPasskeyRegisterOptions = <T = ApiResponse<"/auth/passkey/register/options", "post">>(body?: ApiBody<"/auth/passkey/register/options", "post">) => api.post<T>(`/auth/passkey/register/options`, body)

/** POST /auth/passkey/register/verify */
export const postAuthPasskeyRegisterVerify = <T = ApiResponse<"/auth/passkey/register/verify", "post">>(body?: ApiBody<"/auth/passkey/register/verify", "post">) => api.post<T>(`/auth/passkey/register/verify`, body)

/** DELETE /auth/passkey/:id */
export const deleteAuthPasskeyById = <T = ApiResponse<"/auth/passkey/{credential_id}", "delete">>(id: Id, body?: ApiBody<"/auth/passkey/{credential_id}", "delete">) => api.delete<T>(`/auth/passkey/${id}`, body)

/** GET /auth/totp/status */
export const getAuthTotpStatus = <T = ApiResponse<"/auth/totp/status", "get">>() => api.get<T>(`/auth/totp/status`)

/** POST /auth/totp/setup */
export const postAuthTotpSetup = <T = ApiResponse<"/auth/totp/setup", "post">>(body?: ApiBody<"/auth/totp/setup", "post">) => api.post<T>(`/auth/totp/setup`, body)

/** POST /auth/totp/enable */
export const postAuthTotpEnable = <T = ApiResponse<"/auth/totp/enable", "post">>(body?: ApiBody<"/auth/totp/enable", "post">) => api.post<T>(`/auth/totp/enable`, body)

/** POST /auth/totp/disable */
export const postAuthTotpDisable = <T = ApiResponse<"/auth/totp/disable", "post">>(body?: ApiBody<"/auth/totp/disable", "post">) => api.post<T>(`/auth/totp/disable`, body)

/** POST /auth/totp/recovery-codes */
export const postAuthTotpRecoveryCodes = <T = ApiResponse<"/auth/totp/recovery-codes", "post">>(body?: ApiBody<"/auth/totp/recovery-codes", "post">) => api.post<T>(`/auth/totp/recovery-codes`, body)

/** GET /logos/search */
export const getLogosSearch = <T = ApiResponse<"/logos/search", "get">>(query = "") => api.get<T>(`/logos/search${query}`)

/** POST /logos/from-domain */
export const postLogosFromDomain = <T = ApiResponse<"/logos/from-domain", "post">>(body?: ApiBody<"/logos/from-domain", "post">) => api.post<T>(`/logos/from-domain`, body)

/** GET /export/transactions.csv (fichier) */
export const downloadExportTransactionsCsv = (query = "") => api.download(`/export/transactions.csv${query}`)
