import { cn } from '../../lib/cn'
import { useToast } from '../../store/toast'
import Icon from './Icon'

export function Spinner({ label = 'Loading…', className = '' }) {
  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center gap-3 py-16 text-muted',
        className,
      )}
    >
      <span className="h-7 w-7 animate-spin rounded-full border-2 border-brand-500 border-t-transparent" />
      <span className="text-[12px]">{label}</span>
    </div>
  )
}

export function EmptyState({ icon = 'file', title, description, action, className = '' }) {
  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center gap-3 px-6 py-14 text-center',
        className,
      )}
    >
      <span className="rounded-lg border border-line bg-surface-alt p-2.5 text-muted-light">
        <Icon name={icon} size={20} />
      </span>
      <div>
        <h3 className="type-card-title">{title}</h3>
        {description && <p className="mt-1 max-w-sm text-[12px] text-muted">{description}</p>}
      </div>
      {action}
    </div>
  )
}

export function PageHeader({ title, description, actions, eyebrow }) {
  return (
    <div className="animate-enter mb-7 flex min-w-0 flex-wrap items-end justify-between gap-5">
      <div className="min-w-0">
        {eyebrow && (
          <p className="mb-2 text-[10.5px] font-medium tracking-[0.16em] text-brand-500 uppercase">
            {eyebrow}
          </p>
        )}
        <h1 className="text-balance font-display text-[36px] leading-[1.05] font-normal tracking-[-0.02em] text-ink md:text-[40px]">
          {title}
        </h1>
        {description && (
          <p className="mt-2 max-w-2xl text-[14px] leading-[1.6] text-muted">{description}</p>
        )}
      </div>
      {actions && <div className="flex min-w-0 flex-wrap items-center gap-2">{actions}</div>}
    </div>
  )
}

export function Tabs({ tabs, value, onChange, className = '' }) {
  return (
    <div
      className={cn(
        'inline-flex flex-wrap gap-1 rounded-lg border border-line bg-surface-alt p-1',
        className,
      )}
    >
      {tabs.map((tab) => (
        <button
          key={tab.id}
          type="button"
          onClick={() => onChange(tab.id)}
          className={cn(
            'inline-flex items-center gap-1.5 rounded-[6px] px-3 py-1.5 text-[12px] font-medium transition-all duration-200',
            value === tab.id
              ? 'bg-surface text-ink shadow-[0_1px_4px_rgba(3,89,72,0.1)]'
              : 'text-muted hover:text-ink',
          )}
        >
          {tab.label}
          {tab.count !== undefined && (
            <span className="rounded-[3px] bg-tint px-1.5 text-[10px] text-brand-500">
              {tab.count}
            </span>
          )}
        </button>
      ))}
    </div>
  )
}

const TOAST_STYLES = {
  success: 'border-l-status-success text-ink',
  error: 'border-l-status-danger text-ink',
  info: 'border-l-brand-500 text-ink',
}

const TOAST_ICONS = { success: 'check', error: 'alert', info: 'spark' }
const TOAST_ICON_COLORS = {
  success: 'text-status-success',
  error: 'text-status-danger',
  info: 'text-brand-500',
}

export function Toaster() {
  const toasts = useToast((state) => state.toasts)
  const dismiss = useToast((state) => state.dismiss)

  if (!toasts.length) return null

  return (
    <div className="pointer-events-none fixed right-4 bottom-4 z-[60] flex w-80 flex-col gap-2">
      {toasts.map((toast) => (
        <div
          key={toast.id}
          role="status"
          className={cn(
            'animate-enter pointer-events-auto flex items-start gap-2.5 rounded-lg border border-line border-l-2 bg-surface px-3.5 py-3 text-[12px] shadow-card',
            TOAST_STYLES[toast.type] || TOAST_STYLES.info,
          )}
        >
          <Icon
            name={TOAST_ICONS[toast.type] || 'spark'}
            size={14}
            className={cn(
              'mt-0.5 shrink-0',
              TOAST_ICON_COLORS[toast.type] || TOAST_ICON_COLORS.info,
            )}
          />
          <p className="flex-1 leading-relaxed">{toast.message}</p>
          <button
            type="button"
            onClick={() => dismiss(toast.id)}
            className="text-muted-light hover:text-ink"
            aria-label="Dismiss"
          >
            <Icon name="x" size={13} />
          </button>
        </div>
      ))}
    </div>
  )
}
