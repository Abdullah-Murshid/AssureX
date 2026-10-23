import { api, unwrap } from './client'
import { EP, fill } from './endpoints'

export const listProducts = (params = {}) =>
  unwrap(api.get(EP.products, { params }))

export const getProduct = (productId) =>
  unwrap(api.get(fill(EP.product, { product_id: productId })))

export const createProduct = (payload) => unwrap(api.post(EP.products, payload))
