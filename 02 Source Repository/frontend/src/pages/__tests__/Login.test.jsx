import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
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
import { useAuth } from '../../store/auth'
import Login from '../Login'

const renderLogin = () =>
  render(
    <MemoryRouter initialEntries={['/login']}>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/" element={<div>Dashboard home</div>} />
      </Routes>
    </MemoryRouter>,
  )

describe('Login page', () => {
  beforeEach(() => {
    useAuth.setState({ user: null, stats: null, status: 'anonymous' })
    tokenStore.clear()
    vi.clearAllMocks()
  })

  it('renders the sign-in form and demo accounts', () => {
    renderLogin()
    expect(screen.getByRole('heading', { name: 'Welcome back' })).toBeInTheDocument()
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/^password/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Sign in' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Customer' })).toBeInTheDocument()
  })

  it('fills demo credentials', async () => {
    renderLogin()
    await userEvent.click(screen.getByRole('button', { name: 'Reviewer' }))
    expect(screen.getByLabelText(/email/i)).toHaveValue('reviewer@assurex.com')
    expect(screen.getByLabelText(/^password/i)).toHaveValue('reviewer123')
  })

  it('signs in and navigates to the dashboard', async () => {
    authApi.login.mockResolvedValue({
      access_token: 'signed-token',
      user: { user_id: 'USR-0001', role: 'customer', full_name: 'John Customer' },
    })
    renderLogin()

    await userEvent.type(screen.getByLabelText(/email/i), 'customer@assurex.com')
    await userEvent.type(screen.getByLabelText(/^password/i), 'customer123')
    await userEvent.click(screen.getByRole('button', { name: 'Sign in' }))

    expect(await screen.findByText('Dashboard home')).toBeInTheDocument()
    expect(tokenStore.get()).toBe('signed-token')
  })

  it('shows the API error message on failure', async () => {
    authApi.login.mockRejectedValue({ detail: 'Invalid email or password.' })
    renderLogin()

    await userEvent.type(screen.getByLabelText(/email/i), 'customer@assurex.com')
    await userEvent.type(screen.getByLabelText(/^password/i), 'wrong')
    await userEvent.click(screen.getByRole('button', { name: 'Sign in' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Invalid email or password.')
  })
})

