import { api, downloadFile, unwrap } from './client'
import { EP, fill } from './endpoints'

export const listDocuments = (params = {}) =>
  unwrap(api.get(EP.documents, { params }))

export const uploadDocument = (formData) =>
  unwrap(api.post(EP.documents, formData))

export const getDocument = (docId) =>
  unwrap(api.get(fill(EP.document, { doc_id: docId })))

export const verifyDocument = (docId, payload) =>
  unwrap(api.post(fill(EP.documentVerify, { doc_id: docId }), payload))

export const replaceDocument = (docId, formData) =>
  unwrap(api.post(fill(EP.documentReplace, { doc_id: docId }), formData))

export const deleteDocument = (docId) =>
  unwrap(api.delete(fill(EP.document, { doc_id: docId })))

export const downloadDocument = (docId, filename) =>
  downloadFile(fill(EP.documentDownload, { doc_id: docId }), filename)
