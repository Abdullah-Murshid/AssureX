import { api, downloadFile, unwrap } from './client'
import { EP, fill } from './endpoints'

export const listPolicies = () => unwrap(api.get(EP.policies))

export const getPolicy = (category) =>
  unwrap(api.get(fill(EP.policy, { category })))

export const savePolicy = (category, data) =>
  unwrap(api.put(fill(EP.policy, { category }), { data }))

export const analytics = () => unwrap(api.get(EP.analytics))

export const monitoring = () => unwrap(api.get(EP.monitoring))

export const auditLogs = (params = {}) =>
  unwrap(api.get(EP.auditLogs, { params }))

export const getSettings = () => unwrap(api.get(EP.settings))

export const updateSettings = (settings) =>
  unwrap(api.put(EP.settings, { settings }))

export const exportClaimsCsv = () =>
  downloadFile(EP.exportCsv, 'assurex_claims_export.csv')
