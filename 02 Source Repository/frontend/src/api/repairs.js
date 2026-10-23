import { api, unwrap } from './client'
import { EP } from './endpoints'

export const listRepairs = (params = {}) =>
  unwrap(api.get(EP.repairs, { params }))

export const createRepair = (payload) => unwrap(api.post(EP.repairs, payload))
