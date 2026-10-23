import { cn } from '../../lib/cn'
import Icon from './Icon'

const VARIANTS = {
  primary:
    'bg-brand-500 text-white shadow-[0_1px_4px_rgba(3,89,72,0.2)] hover:bg-brand-600 hover:-translate-y-px',
  secondary:
    'border border-line-input bg-transparent text-brand-500 hover:border-brand-400 hover:text-brand-600',
  ghost: 'text-muted hover:bg-surface-alt hover:text-ink',
  danger: 'bg-status-danger text-white hover:bg-[#8f1c13]',
  success: 'bg-status-success text-white hover:bg-[#0b5340]',
  outline:
    'border border-brand-500/30 bg-brand-500/5 text-brand-500 hover:bg-tint hover:border-brand-500/50',
}

const SIZES = {
  sm: 'h-8 px-3 text-[12px] gap-1.5',
  md: 'h-10 px-4 text-[13px] gap-2',
  lg: 'h-11 px-6 text-[13px] gap-2',
}

export function buttonClasses({ variant = 'primary', size = 'md', className = '' } = {}) {
  return cn(
    'inline-flex items-center justify-center rounded-lg font-medium transition-all duration-200',
    'focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-400',
    'disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:translate-y-0',
    VARIANTS[variant] || VARIANTS.primary,
    SIZES[size] || SIZES.md,
    className,
  )
}

export default function Button({
  children,
  variant = 'primary',
  size = 'md',
  icon,
  loading = false,
  className = '',
  type = 'button',
  disabled,
  ...props
}) {
  return (
    <button
      type={type}
      className={buttonClasses({ variant, size, className })}
      disabled={loading || disabled}
      {...props}
    >
      {loading ? (
        <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-current border-t-transparent" />
      ) : (
        icon && <Icon name={icon} size={size === 'sm' ? 13 : 15} />
      )}
      {children}
    </button>
  )
}
