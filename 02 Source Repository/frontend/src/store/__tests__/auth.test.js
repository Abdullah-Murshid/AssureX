import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('../../api/auth', () => ({
  login: vi.fn(),
  register: vi.fn(),
  logout: vi.fn(),
  me: vi.fn(),
  updateProfile: vi.fn(),
  changePassword: vi.fn(),
}))

import * as authApi from '../../api/auth'
import { tokenStore } from '../../api/client'
import { useAuth } from '../auth'

const resetStore = () =>
  useAuth.setState({ user: null, stats: null, status: 'idle' })

describe('auth store', () => {
  beforeEach(() => {
    resetStore()
    tokenStore.clear()
    vi.clearAllMocks()
  })

  it('logs in, stores the token and exposes the user', async () => {
    authApi.login.mockResolvedValue({
      access_token: 'signed-token',
      user: { user_id: 'USR-0001', role: 'customer', full_name: 'John Customer' },
    })

    const user = await useAuth.getState().login('customer@assurex.com', 'customer123')

    expect(user.user_id).toBe('USR-0001')
    expect(tokenStore.get()).toBe('signed-token')
    expect(useAuth.getState().status).toBe('authenticated')
    expect(authApi.login).toHaveBeenCalledWith('customer@assurex.com', 'customer123')
  })

  it('treats admin as authorised for every role check', async () => {
    useAuth.setState({
      user: { user_id: 'USR-0004', role: 'admin' },
      status: 'authenticated',
    })

    expect(useAuth.getState().hasRole('reviewer')).toBe(true)
    expect(useAuth.getState().hasRole('customer', 'service_center')).toBe(true)
  })

  it('restricts a customer to customer-facing roles', () => {
    useAuth.setState({
      user: { user_id: 'USR-0001', role: 'customer' },
      status: 'authenticated',
    })

    expect(useAuth.getState().hasRole('customer')).toBe(true)
    expect(useAuth.getState().hasRole('reviewer')).toBe(false)
    expect(useAuth.getState().hasRole('admin')).toBe(false)
  })

  it('stays anonymous when no token is stored', async () => {
    await useAuth.getState().hydrate()
    expect(useAuth.getState().status).toBe('anonymous')
    expect(authApi.me).not.toHaveBeenCalled()
  })

  it('hydrates a valid session from a stored token', async () => {
    tokenStore.set('signed-token')
    authApi.me.mockResolvedValue({
      user: { user_id: 'USR-0001', role: 'customer', full_name: 'John Customer' },
      stats: { products: 2, claims: 3 },
    })

    await useAuth.getState().hydrate()

    expect(useAuth.getState().status).toBe('authenticated')
    expect(useAuth.getState().stats).toEqual({ products: 2, claims: 3 })
  })

  it('clears an expired token during hydration', async () => {
    tokenStore.set('expired')
    authApi.me.mockRejectedValue(new Error('401'))

    await useAuth.getState().hydrate()

    expect(useAuth.getState().status).toBe('anonymous')
    expect(tokenStore.get()).toBeNull()
  })

  it('logs out and clears state', async () => {
    tokenStore.set('signed-token')
    useAuth.setState({ user: { user_id: 'USR-0001' }, status: 'authenticated' })
    authApi.logout.mockResolvedValue({ detail: 'ok' })

    await useAuth.getState().logout()

    expect(tokenStore.get()).toBeNull()
    expect(useAuth.getState().status).toBe('anonymous')
    expect(useAuth.getState().user).toBeNull()
  })
})
