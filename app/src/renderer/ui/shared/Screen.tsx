import type { ReactNode } from 'react'

interface ScreenProps {
  children: ReactNode
}

/** Centered, generous layout shared by every full-window state. */
export function Screen({ children }: ScreenProps) {
  return (
    <main className="flex min-h-screen items-center justify-center bg-surface px-8 py-16">
      <div className="w-full max-w-md text-center">{children}</div>
    </main>
  )
}
