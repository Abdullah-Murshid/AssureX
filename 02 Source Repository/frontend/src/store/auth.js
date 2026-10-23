import { create } from 'zustand'

import * as authApi from '../api/auth'
import { tokenStore } from '../api/client'

export const useAuth = create((set, get) => ({
  status: 'idle',
  user: null,
  stats: null,

  isAuthenticated: () => get().status === 'authenticated',

  hasRole: (...roles) => {
    const role = get().user?.role
    if (!role) return false
    return role === 'admin' || roles.flat().includes(role)
  },

  login: async (email, password) => {
    const data = await authApi.login(email, password)
    tokenStore.set(data.access_token)
    set({ user: data.user, status: 'authenticated' })
    return data.user
  },

  register: async (payload) => {
    const data = await authApi.register(payload)
    tokenStore.set(data.access_token)
    set({ user: data.user, status: 'authenticated' })
    return data.user
  },

  hydrate: async () => {
    if (get().status === 'loading' || get().status === 'authenticated') return
    if (!tokenStore.get()) {
      set({ status: 'anonymous' })
      return
    }
    set({ status: 'loading' })
    try {
      const data = await authApi.me()
      set({ user: data.user, stats: data.stats, status: 'authenticated' })
    } catch {
      tokenStore.clear()
      set({ user: null, stats: null, status: 'anonymous' })
    }
  },

  refresh: async () => {
    const data = await authApi.me()
    set({ user: data.user, stats: data.stats, status: 'authenticated' })
    return data.user
  },

  updateProfile: async (payload) => {
    const data = await authApi.updateProfile(payload)
    set({ user: data.user })
    return data.user
  },

  logout: async () => {
    try {
      await authApi.logout()
    } catch {
      /* session may already be gone */
    }
    tokenStore.clear()
    set({ user: null, stats: null, status: 'anonymous' })
  },

  reset: () => {
    tokenStore.clear()
    set({ user: null, stats: null, status: 'anonymous' })
  },
}))
