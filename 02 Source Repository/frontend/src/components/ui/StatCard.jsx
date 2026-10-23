import { cn } from '../../lib/cn'
import CountUp from './CountUp'
import Icon from './Icon'

const ICON_TONES = {
  brand: 'text-brand-500',
  success: 'text-status-success',
  warning: 'text-status-warning',
  danger: 'text-status-danger',
  neutral: 'text-muted-light',
}

export default function StatCard({
  label,
  value,
  hint,
  icon = 'trend',
  tone = 'brand',
  className = '',
  onClick,
}) {
  const Tag = onClick ? 'button' : 'div'
  const numeric = typeof value === 'number' && Number.isFinite(value)

  return (
    <Tag
      type={onClick ? 'button' : undefined}
      onClick={onClick}
      className={cn(
        'group flex min-w-0 flex-col justify-between rounded-2xl border border-line bg-surface p-4 text-left shadow-card-soft transition-colors duration-200',
        onClick && 'hover:border-brand-500/40 hover:bg-[#FCFCFA]',
        className,
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <p className="text-[10.5px] font-medium tracking-[0.12em] text-muted-light uppercase">
          {label}
        </p>
        <Icon name={icon} size={15} className={cn('mt-0.5', ICON_TONES[tone] || ICON_TONES.brand)} />
      </div>
      <div className="mt-3">
        <p className="font-display text-[34px] leading-none text-ink">
          {numeric ? <CountUp value={value} /> : value}
        </p>
        {hint && <p className="mt-1.5 text-[11px] text-muted">{hint}</p>}
      </div>
    </Tag>
  )
}
