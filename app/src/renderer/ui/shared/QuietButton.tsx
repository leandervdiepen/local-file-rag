import type { ButtonHTMLAttributes } from 'react'

type QuietButtonProps = ButtonHTMLAttributes<HTMLButtonElement>

/** A control that is present without competing with the content for attention. */
export function QuietButton({ className = '', ...props }: QuietButtonProps) {
  return (
    <button
      type="button"
      className={`focus-ring rounded-control px-2 py-1 text-xs text-ink-muted transition-colors hover:bg-border/40 hover:text-ink ${className}`}
      {...props}
    />
  )
}
