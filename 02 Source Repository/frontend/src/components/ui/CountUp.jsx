import { useEffect, useRef, useState } from 'react'

const REDUCED_MOTION =
  typeof window !== 'undefined' &&
  window.matchMedia?.('(prefers-reduced-motion: reduce)').matches

/**
 * Animates an integer from 0 to `value` once, matching the short numeric
 * emphasis used on iwarranty.ai. Visual only — the value itself is unchanged.
 */
export default function CountUp({ value, duration = 900, className = '' }) {
  const [display, setDisplay] = useState(REDUCED_MOTION ? value : 0)
  const frame = useRef(null)

  useEffect(() => {
    if (REDUCED_MOTION || typeof value !== 'number' || !Number.isFinite(value)) {
      return undefined
    }

    let start = null
    const from = 0

    const tick = (now) => {
      if (start === null) start = now
      const progress = Math.min(1, Math.max(0, (now - start) / duration))
      const eased = 1 - (1 - progress) ** 3
      setDisplay(Math.round(from + (value - from) * eased))
      if (progress < 1) frame.current = requestAnimationFrame(tick)
    }

    frame.current = requestAnimationFrame(tick)
    return () => {
      if (frame.current) cancelAnimationFrame(frame.current)
    }
  }, [value, duration])

  return <span className={className}>{display}</span>
}
