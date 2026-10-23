import { api, unwrap } from './client'
import { EP, fill } from './endpoints'

export const login = (email, password) =>
  unwrap(api.post(EP.login, { email, password }))

export const register = (payload) => unwrap(api.post(EP.register, payload))

export const logout = () => unwrap(api.post(EP.logout))

export const me = () => unwrap(api.get(EP.me))

export const updateProfile = (payload) => unwrap(api.patch(EP.me, payload))

export const changePassword = (current_password, new_password) =>
  unwrap(api.post(EP.changePassword, { current_password, new_password }))

export { fill }
