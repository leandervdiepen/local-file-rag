import type { ReactNode } from 'react'

interface ScreenProps {
  children: ReactNode
}

/** A centred message with one thing to do, for every state before search exists. */
export function Screen({ children }: ScreenProps) {
  return (
    <main className="flex min-h-screen items-center justify-center bg-surface px-8 py-16">
      <div className="w-full max-w-sm text-center">{children}</div>
    </main>
  )
}
