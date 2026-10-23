import { cn } from '../../lib/cn'

const TONES = {
  neutral: 'border-line bg-surface-alt text-muted',
  info: 'border-brand-500/20 bg-tint text-brand-500',
  success: 'border-status-success/20 bg-status-success/[0.07] text-status-success',
  warning: 'border-status-warning/25 bg-status-warning/[0.08] text-status-warning',
  danger: 'border-status-danger/20 bg-status-danger/[0.06] text-status-danger',
  brand: 'border-brand-500/20 bg-tint text-brand-500',
}

export default function Badge({ children, tone = 'neutral', className = '', dot = false }) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-[4px] border px-2 py-[3px] text-[10px] font-medium tracking-[0.06em] whitespace-nowrap uppercase',
        TONES[tone] || TONES.neutral,
        className,
      )}
    >
      {dot && <span className="h-1.5 w-1.5 rounded-full bg-current" />}
      {children}
    </span>
  )
}
