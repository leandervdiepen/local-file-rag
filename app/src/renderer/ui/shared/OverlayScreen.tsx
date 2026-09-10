import type { ReactNode } from 'react'
import { Button } from './Button'
import { useEscapeToClose } from './useEscapeToClose'

interface OverlayScreenProps {
  title: string
  actions?: ReactNode
  onClose: () => void
  children: ReactNode
}

/** A full screen that sits over search: one title, its actions, and Close or Escape to leave. */
export function OverlayScreen({ title, actions, onClose, children }: OverlayScreenProps) {
  useEscapeToClose(onClose)

  return (
    <section className="fixed inset-0 z-10 overflow-auto bg-surface" aria-label={title}>
      <div className="mx-auto w-full max-w-3xl px-8 py-10">
        <header className="flex items-center gap-2">
          <h1 className="flex-1 text-lg font-medium text-ink">{title}</h1>
          {actions}
          <Button onClick={onClose}>Close</Button>
        </header>
        {children}
      </div>
    </section>
  )
}
