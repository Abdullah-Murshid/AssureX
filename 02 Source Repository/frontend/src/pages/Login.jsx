import { useEffect, useState } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'

import { errorMessage } from '../api/client'
import AuthLayout from '../components/layout/AuthLayout'
import Button from '../components/ui/Button'
import { Input } from '../components/ui/Fields'
import Icon from '../components/ui/Icon'
import { useAuth } from '../store/auth'

const DEMO = [
  { label: 'Customer', email: 'customer@assurex.com', password: 'customer123' },
  { label: 'Reviewer', email: 'reviewer@assurex.com', password: 'reviewer123' },
  { label: 'Admin', email: 'admin@assurex.com', password: 'admin123' },
]

export default function Login() {
  const login = useAuth((state) => state.login)
  const status = useAuth((state) => state.status)
  const navigate = useNavigate()
  const location = useLocation()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (status === 'authenticated') {
      navigate(location.state?.from || '/', { replace: true })
    }
  }, [status, navigate, location.state])

  if (status === 'authenticated') {
    return <Navigate to="/" replace />
  }

  const onSubmit = async (event) => {
    event.preventDefault()
    setError('')
    setLoading(true)
    try {
      await login(email.trim(), password)
      navigate(location.state?.from || '/', { replace: true })
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  const fillDemo = (demo) => {
    setEmail(demo.email)
    setPassword(demo.password)
    setError('')
  }

  return (
    <AuthLayout
      title="Welcome back"
      subtitle="Sign in to review, submit and adjudicate warranty claims."
      footer={
        <>
          No account?{' '}
          <Link to="/register" className="font-medium text-brand-500 hover:text-brand-600">
            Create one
          </Link>
        </>
      }
    >
      <form onSubmit={onSubmit} className="space-y-4" noValidate>
        <Input
          label="Email"
          type="email"
          autoComplete="email"
          required
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          placeholder="you@company.com"
        />

        <div className="relative">
          <Input
            label="Password"
            type={showPassword ? 'text' : 'password'}
            autoComplete="current-password"
            required
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            placeholder="••••••••"
          />
          <button
            type="button"
            onClick={() => setShowPassword((value) => !value)}
            className="absolute right-3 bottom-2.5 rounded p-1 text-muted-light hover:text-ink"
            aria-label={showPassword ? 'Hide password' : 'Show password'}
          >
            <Icon name={showPassword ? 'x' : 'eye'} size={16} />
          </button>
        </div>

        {error && (
          <p role="alert" className="rounded-lg border border-status-danger/20 bg-status-danger/[0.05] px-3 py-2 text-[12px] text-status-danger">
            {error}
          </p>
        )}

        <Button type="submit" loading={loading} className="w-full">
          Sign in
        </Button>
      </form>

      <div className="mt-7">
        <p className="text-center text-[10.5px] tracking-[0.12em] text-muted-light uppercase">Demo accounts</p>
        <div className="mt-2 grid grid-cols-3 gap-2">
          {DEMO.map((demo) => (
            <button
              key={demo.email}
              type="button"
              onClick={() => fillDemo(demo)}
              className="rounded-lg border border-line bg-surface px-2 py-1.5 text-[11px] font-medium text-muted transition-colors duration-200 hover:border-brand-500/30 hover:text-brand-600"
            >
              {demo.label}
            </button>
          ))}
        </div>
      </div>
    </AuthLayout>
  )
}


