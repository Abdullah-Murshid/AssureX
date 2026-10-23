/**
 * Every backend path used by the app, relative to the `/api/v1` base URL.
 * `npm test` asserts each template exists in `openapi.json` (contract test).
 */
export const EP = {
  health: '/health',
  models: '/system/models',
  info: '/system/info',

  login: '/auth/login',
  register: '/auth/register',
  logout: '/auth/logout',
  me: '/auth/me',
  changePassword: '/auth/change-password',

  products: '/products',
  product: '/products/{product_id}',

  warranties: '/warranties',
  warranty: '/warranties/{product_id}',
  alerts: '/alerts',
  dismissAlert: '/alerts/{product_id}/dismiss',

  documents: '/documents',
  document: '/documents/{doc_id}',
  documentDownload: '/documents/{doc_id}/download',
  documentVerify: '/documents/{doc_id}/verify',
  documentReplace: '/documents/{doc_id}/replace',

  repairs: '/repairs',

  claims: '/claims',
  precheck: '/claims/precheck',
  importCsv: '/claims/import-csv',
  claim: '/claims/{claim_id}',
  claimHistory: '/claims/{claim_id}/history',
  claimDossier: '/claims/{claim_id}/dossier',
  summaryCard: '/claims/{claim_id}/summary-card',
  attachDocument: '/claims/{claim_id}/documents/{doc_id}',
  reportPdf: '/claims/{claim_id}/report.pdf',
  reportMd: '/claims/{claim_id}/report.md',

  notifications: '/notifications',
  notificationsUnread: '/notifications/unread-count',
  notificationRead: '/notifications/{notification_id}/read',
  notificationsReadAll: '/notifications/read-all',

  reviewQueue: '/review/queue',
  reviewStats: '/review/stats',
  reviewDecision: '/review/{claim_id}/decision',

  policies: '/admin/policies',
  policy: '/admin/policies/{category}',
  analytics: '/admin/analytics',
  monitoring: '/admin/monitoring',
  auditLogs: '/admin/audit-logs',
  exportCsv: '/admin/export/claims.csv',
  settings: '/admin/settings',
}

export function fill(template, params = {}) {
  return template.replace(/\{(\w+)\}/g, (_, key) => {
    const value = params[key]
    if (value === undefined || value === null) {
      throw new Error(`Missing path parameter '${key}' for ${template}`)
    }
    return encodeURIComponent(String(value))
  })
}
