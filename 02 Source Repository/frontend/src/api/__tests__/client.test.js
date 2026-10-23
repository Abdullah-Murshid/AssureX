import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { api, errorMessage, tokenStore } from '../client'

const okAdapter = (capture) => async (config) => {
  capture.config = config
  return { data: { ok: true }, status: 200, statusText: 'OK', headers: {}, config }
}

describe('api client', () => {
  beforeEach(() => {
    tokenStore.clear()
    vi.restoreAllMocks()
  })

  afterEach(() => {
    api.defaults.adapter = undefined
  })

  it('attaches the bearer token to requests', async () => {
    tokenStore.set('signed-token')
    const capture = {}
    api.defaults.adapter = okAdapter(capture)

    const response = await api.get('/auth/me')

    expect(response.data).toEqual({ ok: true })
    expect(capture.config.headers.Authorization).toBe('Bearer signed-token')
  })

  it('omits the Authorization header when signed out', async () => {
    const capture = {}
    api.defaults.adapter = okAdapter(capture)

    await api.get('/health')

    expect(capture.config.headers.Authorization).toBeUndefined()
  })

  it('clears the token and emits an event on 401', async () => {
    tokenStore.set('expired-token')
    const listener = vi.fn()
    window.addEventListener('assurex:unauthorized', listener)

    api.defaults.adapter = async () => {
      const error = new Error('Unauthorized')
      error.config = {}
      error.response = { status: 401, data: { detail: 'Invalid or expired token' } }
      throw error
    }

    await expect(api.get('/claims')).rejects.toMatchObject({
      detail: 'Invalid or expired token',
    })
    expect(tokenStore.get()).toBeNull()
    expect(listener).toHaveBeenCalledTimes(1)

    window.removeEventListener('assurex:unauthorized', listener)
  })

  it('normalises API error messages', () => {
    expect(errorMessage({ detail: 'Product not found.' })).toBe('Product not found.')
    expect(errorMessage({ response: { status: 503 } })).toMatch(/models are still loading/i)
    expect(errorMessage(new Error('Network down'))).toBe('Network down')
  })
})
