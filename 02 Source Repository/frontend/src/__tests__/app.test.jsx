import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it } from 'vitest'

import App from '../App'
import { tokenStore } from '../api/client'
import { useAuth } from '../store/auth'

describe('App routing', () => {
  beforeEach(() => {
    localStorage.clear()
    tokenStore.clear()
    useAuth.setState({ user: null, stats: null, status: 'idle' })
    window.history.pushState({}, '', '/')
  })

  it('redirects anonymous visitors to the login page', async () => {
    render(<App />)
    expect(await screen.findByRole('heading', { name: 'Welcome back' })).toBeInTheDocument()
  })
})
