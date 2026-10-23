import axios from 'axios'

const TOKEN_KEY = 'assurex.token'

export const tokenStore = {
  get() {
    try {
      return localStorage.getItem(TOKEN_KEY)
    } catch {
      return null
    }
  },
  set(token) {
    try {
      localStorage.setItem(TOKEN_KEY, token)
    } catch {
      /* ignore storage errors */
    }
  },
  clear() {
    try {
      localStorage.removeItem(TOKEN_KEY)
    } catch {
      /* ignore storage errors */
    }
  },
}

export const api = axios.create({
  baseURL: '/api/v1',
  timeout: 120_000,
})

api.interceptors.request.use((config) => {
  const token = tokenStore.get()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error.response?.status
    const detail = error.response?.data?.detail

    if (status === 401) {
      tokenStore.clear()
      window.dispatchEvent(new Event('assurex:unauthorized'))
    }

    error.detail =
      detail ||
      (typeof error.response?.data === 'string' ? error.response.data : null) ||
      error.message ||
      'Request failed'
    return Promise.reject(error)
  },
)

export function errorMessage(error) {
  if (error?.detail) return error.detail
  if (error?.response?.status === 503) {
    return 'AI models are still loading. Please retry in a moment.'
  }
  return error?.message || 'Something went wrong.'
}

export const unwrap = (promise) => promise.then((response) => response.data)

/** Fetch an authenticated binary resource (summary card, PDF, CSV). */
export async function fetchBlob(path) {
  const response = await api.get(path, { responseType: 'blob' })
  return response.data
}

export function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}

export async function downloadFile(path, filename) {
  const blob = await fetchBlob(path)
  downloadBlob(blob, filename)
}
