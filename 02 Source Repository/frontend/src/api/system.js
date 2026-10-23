import { api, unwrap } from './client'
import { EP } from './endpoints'

export const health = () => unwrap(api.get(EP.health))
export const modelStatus = () => unwrap(api.get(EP.models))
export const systemInfo = () => unwrap(api.get(EP.info))
