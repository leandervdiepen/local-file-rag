// The app's tokens, dark theme, copied from app/src/renderer/tokens.css.
// The footage is recorded in dark mode, so the frame around it is the same surface.
export const color = {
  ink: 'oklch(94% 0.004 60)',
  inkMuted: 'oklch(72% 0.008 60)',
  surface: 'oklch(16% 0.006 60)',
  border: 'oklch(30% 0.008 60)',
  accent: 'oklch(74% 0.14 255)',
  heat: 'oklch(70% 0.2 25)',
}

export const shadowControl = '0 0 0 1px oklch(1 0 0 / 0.12), 0 1px 2px oklch(0 0 0 / 0.4)'

export const font = {
  sans: "'Inter Variable', ui-sans-serif, system-ui, sans-serif",
  mono: "'JetBrains Mono Variable', ui-monospace, 'SF Mono', monospace",
}

/**
 * The app's ramp, scaled 2.5x for a 1920 frame that is watched at half size.
 * Line height loosens as the size drops and tracking tightens as it grows,
 * the same rule the app follows.
 */
export const type = {
  xs: { fontSize: 28, lineHeight: '40px', letterSpacing: '0' },
  sm: { fontSize: 32, lineHeight: '48px', letterSpacing: '0' },
  base: { fontSize: 38, lineHeight: '54px', letterSpacing: '0' },
  lg: { fontSize: 50, lineHeight: '68px', letterSpacing: '-0.01em' },
  xl: { fontSize: 60, lineHeight: '80px', letterSpacing: '-0.015em' },
  display: { fontSize: 96, lineHeight: '108px', letterSpacing: '-0.02em' },
}

export const FPS = 30
/** A state flip is 120 ms in the app. The heatmap fade is 200. Nothing here is longer. */
export const FLIP = Math.round(0.12 * FPS)
export const FADE = Math.round(0.2 * FPS)
