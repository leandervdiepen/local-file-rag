import type { ButtonHTMLAttributes } from 'react'

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement>

/** The one raised control. Everything else on a screen is ink on the surface. */
export function Button({ className = '', ...props }: ButtonProps) {
  return (
    <button
      type="button"
      className={`focus-ring rounded-control bg-surface px-3 py-1.5 text-sm text-ink shadow-control transition-colors hover:bg-border/40 disabled:opacity-40 disabled:hover:bg-surface ${className}`}
      {...props}
    />
  )
}
