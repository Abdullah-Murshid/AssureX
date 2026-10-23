import { useId } from 'react'

import { cn } from '../../lib/cn'

const CONTROL =
  'w-full rounded-lg border border-line bg-surface px-3 text-[13px] text-ink placeholder:text-muted-light transition-colors duration-200 focus:border-brand-500 focus:ring-4 focus:ring-brand-500/10 focus:outline-none disabled:cursor-not-allowed disabled:bg-surface-alt disabled:opacity-70'

export function Field({ label, htmlFor, hint, error, required, children, className = '' }) {
  return (
    <div className={cn('space-y-1.5', className)}>
      {label && (
        <label htmlFor={htmlFor} className="block text-[12px] font-medium text-ink/80">
          {label}
          {required && <span className="ml-1 text-status-danger">*</span>}
        </label>
      )}
      {children}
      {hint && !error && <p className="text-[11px] text-muted-light">{hint}</p>}
      {error && <p className="text-[11px] text-status-danger">{error}</p>}
    </div>
  )
}

export function Input({ label, hint, error, className = '', id, required, ...props }) {
  const autoId = useId()
  const inputId = id || autoId
  return (
    <Field
      label={label}
      htmlFor={inputId}
      hint={hint}
      error={error}
      required={required}
      className={className}
    >
      <input
        id={inputId}
        className={cn(CONTROL, 'h-10', error && 'border-status-danger/60')}
        aria-invalid={Boolean(error)}
        {...props}
      />
    </Field>
  )
}

export function Select({ label, hint, error, className = '', id, required, children, ...props }) {
  const autoId = useId()
  const selectId = id || autoId
  return (
    <Field
      label={label}
      htmlFor={selectId}
      hint={hint}
      error={error}
      required={required}
      className={className}
    >
      <select
        id={selectId}
        className={cn(CONTROL, 'h-10 appearance-none pr-8', error && 'border-status-danger/60')}
        {...props}
      >
        {children}
      </select>
    </Field>
  )
}

export function Textarea({ label, hint, error, className = '', id, required, rows = 3, ...props }) {
  const autoId = useId()
  const textareaId = id || autoId
  return (
    <Field
      label={label}
      htmlFor={textareaId}
      hint={hint}
      error={error}
      required={required}
      className={className}
    >
      <textarea
        id={textareaId}
        rows={rows}
        className={cn(CONTROL, 'py-2.5', error && 'border-status-danger/60')}
        {...props}
      />
    </Field>
  )
}

export function Checkbox({ label, hint, className = '', id, ...props }) {
  const autoId = useId()
  const checkboxId = id || autoId
  return (
    <div className={cn('flex items-start gap-2.5', className)}>
      <input
        id={checkboxId}
        type="checkbox"
        className="mt-0.5 h-4 w-4 rounded-[4px] border-line-input bg-surface accent-brand-500"
        {...props}
      />
      <div>
        <label htmlFor={checkboxId} className="text-[13px] text-ink">
          {label}
        </label>
        {hint && <p className="text-[11px] text-muted-light">{hint}</p>}
      </div>
    </div>
  )
}
