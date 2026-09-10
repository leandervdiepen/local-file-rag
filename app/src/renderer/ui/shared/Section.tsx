import type { ReactNode } from 'react'

interface SectionProps {
  title: string
  hint?: string
  children: ReactNode
}

/** One titled block of a screen. The rhythm between blocks lives here, so every screen shares it. */
export function Section({ title, hint, children }: SectionProps) {
  return (
    <section className="mt-10">
      <h2 className="text-sm font-medium text-ink">{title}</h2>
      {hint && <p className="mt-1 max-w-prose text-xs text-ink-muted">{hint}</p>}
      {children}
    </section>
  )
}
