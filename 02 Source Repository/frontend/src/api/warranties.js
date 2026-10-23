import { api, unwrap } from './client'
import { EP, fill } from './endpoints'

export const listWarranties = (params = {}) =>
  unwrap(api.get(EP.warranties, { params }))

export const getWarranty = (productId) =>
  unwrap(api.get(fill(EP.warranty, { product_id: productId })))

export const listAlerts = (params = {}) => unwrap(api.get(EP.alerts, { params }))

export const dismissAlert = (productId) =>
  unwrap(api.post(fill(EP.dismissAlert, { product_id: productId })))
