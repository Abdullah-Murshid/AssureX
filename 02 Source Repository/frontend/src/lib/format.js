const DATE_FMT = new Intl.DateTimeFormat('en-US', {
  year: 'numeric',
  month: 'short',
  day: 'numeric',
})

const DATETIME_FMT = new Intl.DateTimeFormat('en-US', {
  year: 'numeric',
  month: 'short',
  day: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
})

const MONEY_FMT = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
})

export function titleCase(value) {
  if (!value) return '—'
  return String(value)
    .replace(/[_-]+/g, ' ')
    .replace(/\b\w/g, (char) => char.toUpperCase())
}

export function formatDate(value) {
  if (!value) return '—'
  const date = new Date(`${value}`.length === 10 ? `${value}T00:00:00` : value)
  return Number.isNaN(date.getTime()) ? String(value) : DATE_FMT.format(date)
}

export function formatDateTime(value) {
  if (!value) return '—'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? String(value) : DATETIME_FMT.format(date)
}

export function formatCurrency(value) {
  if (value === null || value === undefined || value === '') return '—'
  return MONEY_FMT.format(Number(value))
}

export function formatPercent(value, digits = 1) {
  if (value === null || value === undefined) return '—'
  return `${(Number(value) * 100).toFixed(digits)}%`
}

export function formatDays(value) {
  if (value === null || value === undefined) return '—'
  const days = Number(value)
  if (days < 0) return `${Math.abs(days)} days ago`
  if (days === 0) return 'Today'
  return `${days} days`
}

export function initials(name) {
  return (
    String(name || '?')
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((part) => part[0].toUpperCase())
      .join('') || '?'
  )
}

export function truncate(value, length = 80) {
  if (!value) return ''
  const text = String(value)
  return text.length > length ? `${text.slice(0, length)}…` : text
}
