import { useEffect, useRef } from 'react'
import { opacityOf } from '../../domain/heatmap'

interface HeatmapOverlayProps {
  values: number[][]
  threshold: number
}

// Read from the same token the rest of the app uses, so the overlay matches
// the theme instead of carrying its own idea of the heat colour.
function heatColor(): string {
  const token = getComputedStyle(document.documentElement).getPropertyValue('--color-heat').trim()
  return token || 'oklch(62% 0.21 25)'
}

/**
 * Draws the patch grid over the page.
 *
 * The canvas is the size of the grid, one pixel per patch, and CSS stretches
 * it to the page. The browser's own smoothing then does the one-patch blur
 * the design asks for, which is cheaper and steadier than blurring by hand.
 */
export function HeatmapOverlay({ values, threshold }: HeatmapOverlayProps) {
  const canvas = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const element = canvas.current
    const context = element?.getContext('2d')
    if (!element || !context) return

    const rows = values.length
    const cols = values[0]?.length ?? 0
    element.width = cols
    element.height = rows
    context.clearRect(0, 0, cols, rows)

    const color = heatColor()
    values.forEach((row, y) =>
      row.forEach((value, x) => {
        const opacity = opacityOf(value, threshold)
        if (opacity <= 0) return
        context.globalAlpha = opacity
        context.fillStyle = color
        context.fillRect(x, y, 1, 1)
      }),
    )
  }, [values, threshold])

  return (
    <canvas
      ref={canvas}
      aria-hidden
      className="pointer-events-none absolute inset-0 h-full w-full motion-safe:transition-opacity motion-safe:duration-200"
    />
  )
}
