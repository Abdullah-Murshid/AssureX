import { Link } from 'react-router-dom'

const STEPS = [
  {
    step: '01',
    title: 'Submit the claim',
    text: 'Product, incident and evidence captured in one guided intake.',
  },
  {
    step: '02',
    title: 'Run dual-model adjudication',
    text: 'Tabular ML and vision agree, disagree or escalate with a confidence trail.',
  },
  {
    step: '03',
    title: 'Resolve with a reviewer',
    text: 'Policy rules, contradictions and overrides recorded in the audit trail.',
  },
]

export default function AuthLayout({ title, subtitle, children, footer }) {
  return (
    <div className="grid min-h-screen bg-background lg:grid-cols-[1.05fr_1fr]">
      <div className="relative hidden flex-col justify-between border-r border-line bg-surface-alt p-12 lg:flex xl:p-14">
        <Link to="/login" className="flex items-center gap-2.5">
          <span className="flex h-9 w-9 items-center justify-center rounded-[8px] bg-brand-500 font-sans text-[17px] font-semibold leading-none text-white">
            A
          </span>
          <span className="leading-tight">
            <span className="block text-[15px] font-semibold text-ink">AssureX</span>
            <span className="block text-[9px] tracking-[0.18em] text-muted-light uppercase">
              Claim Engine
            </span>
          </span>
        </Link>

        <div className="max-w-[460px]">
          <p className="mb-4 text-[10.5px] font-medium tracking-[0.16em] text-brand-500 uppercase">
            Warranty operations platform
          </p>
          <h1 className="text-balance font-display text-[44px] leading-[1.05] font-normal tracking-[-0.02em] text-ink xl:text-[50px]">
            Every claim, decided on evidence.
          </h1>
          <p className="mt-5 max-w-[400px] text-[15px] leading-[1.65] text-muted">
            A single record connects products, documents and repair history to a
            policy-aware decision — with both models and the reviewer on the same page.
          </p>

          <ol className="mt-9 border-t border-line">
            {STEPS.map((item) => (
              <li
                key={item.step}
                className="grid grid-cols-[2.25rem_1fr] gap-4 border-b border-line py-4"
              >
                <span className="font-sans text-[11px] leading-5 tabular-nums text-brand-500">{item.step}</span>
                <span>
                  <span className="block text-[13px] font-semibold text-ink">{item.title}</span>
                  <span className="mt-0.5 block text-[12px] leading-[1.6] text-muted">
                    {item.text}
                  </span>
                </span>
              </li>
            ))}
          </ol>
        </div>

        <p className="text-[10.5px] tracking-[0.04em] text-muted-light">
          AssureX Claim Engine · NextWave AI & ML · REST API v2.0.0
        </p>
      </div>

      <div className="flex items-center justify-center px-5 py-12 sm:px-8">
        <div className="w-full max-w-[360px]">
          <div className="mb-10 flex items-center gap-2.5 lg:hidden">
            <span className="flex h-8 w-8 items-center justify-center rounded-[8px] bg-brand-500 font-sans text-[15px] font-semibold leading-none text-white">
              A
            </span>
            <span className="text-[14px] font-semibold text-ink">AssureX Claim Engine</span>
          </div>

          <h2 className="font-display text-[34px] leading-[1.1] font-normal tracking-[-0.02em] text-ink">
            {title}
          </h2>
          <p className="mt-2 text-[13px] leading-[1.6] text-muted">{subtitle}</p>

          <div className="mt-8">{children}</div>

          {footer && <div className="mt-7 text-center text-[12px] text-muted">{footer}</div>}
        </div>
      </div>
    </div>
  )
}
