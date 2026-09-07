import type { ButtonHTMLAttributes } from 'react'

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement>

export function Button({ className = '', ...props }: ButtonProps) {
  return (
    <button
      type="button"
      className={`rounded-control border border-border px-4 py-2 text-sm text-ink transition-colors hover:bg-border/40 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent ${className}`}
      {...props}
    />
  )
}
