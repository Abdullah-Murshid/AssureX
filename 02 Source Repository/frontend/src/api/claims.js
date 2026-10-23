import { api, downloadFile, unwrap } from './client'
import { EP, fill } from './endpoints'

export const listClaims = (params = {}) =>
  unwrap(api.get(EP.claims, { params }))

export const getClaim = (claimId) =>
  unwrap(api.get(fill(EP.claim, { claim_id: claimId })))

export const getClaimHistory = (claimId) =>
  unwrap(api.get(fill(EP.claimHistory, { claim_id: claimId })))

export const precheckClaim = (payload) => unwrap(api.post(EP.precheck, payload))

export const submitClaim = (formData) => unwrap(api.post(EP.claims, formData))

export const importClaimsCsv = (formData) =>
  unwrap(api.post(EP.importCsv, formData))

export const attachDocument = (claimId, docId) =>
  unwrap(api.post(fill(EP.attachDocument, { claim_id: claimId, doc_id: docId })))

export const downloadSummaryCard = (claimId) =>
  downloadFile(fill(EP.summaryCard, { claim_id: claimId }), `${claimId}_summary_card.png`)

export const downloadReport = (claimId, format = 'pdf') =>
  format === 'md'
    ? downloadFile(fill(EP.reportMd, { claim_id: claimId }), `${claimId}_report.md`)
    : downloadFile(fill(EP.reportPdf, { claim_id: claimId }), `${claimId}_adjudication_report.pdf`)
