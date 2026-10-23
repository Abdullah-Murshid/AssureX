import { useEffect, useState } from 'react'

import { fetchBlob } from '../../api/client'
import { cn } from '../../lib/cn'

/** Renders an authenticated API image (summary card) via a blob URL. */
export default function AuthedImage({ path, alt = '', className = '' }) {
  const [src, setSrc] = useState(null)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    let cancelled = false
    let objectUrl = null

    fetchBlob(path)
      .then((blob) => {
        if (cancelled) return
        objectUrl = URL.createObjectURL(blob)
        setSrc(objectUrl)
      })
      .catch(() => {
        if (!cancelled) setFailed(true)
      })

    return () => {
      cancelled = true
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [path])

  if (failed) {
    return (
      <div
        className={cn(
          'flex aspect-square items-center justify-center rounded-[10px] border border-line bg-surface-alt text-[11px] text-muted-light',
          className,
        )}
      >
        Summary card unavailable
      </div>
    )
  }

  if (!src) {
    return (
      <div
        className={cn(
          'aspect-square animate-pulse rounded-[10px] border border-line bg-surface-alt',
          className,
        )}
      />
    )
  }

  return (
    <img
      src={src}
      alt={alt}
      className={cn('rounded-[10px] border border-line', className)}
    />
  )
}
