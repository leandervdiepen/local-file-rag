import { Easing, interpolate } from 'remotion'

/** The app's one curve: a standard ease-out, cubic-bezier(0, 0, 0.2, 1). */
export const easeOut = Easing.bezier(0, 0, 0.2, 1)

/** Opacity that fades in over `fade` frames from `start` and out over `fade` frames before `end`. */
export function fadeInOut(frame: number, start: number, end: number, fade: number): number {
  const rise = interpolate(frame, [start, start + fade], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: easeOut,
  })
  const fall = interpolate(frame, [end - fade, end], [1, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: easeOut,
  })
  return Math.min(rise, fall)
}

/** A fade in only. Used where the next thing cuts rather than dissolves. */
export function fadeIn(frame: number, start: number, fade: number): number {
  return interpolate(frame, [start, start + fade], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: easeOut,
  })
}

/**
 * Pixels of remaining travel for something settling into place.
 *
 * Text that only fades reads as a slide deck. A few pixels of movement on the
 * way in reads as the thing arriving, and it is over before anyone could call
 * it an animation. Nothing here travels further than `distance`, which is
 * small on purpose.
 */
export function rise(frame: number, start: number, span: number, distance = 14): number {
  return interpolate(frame, [start, start + span], [distance, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: easeOut,
  })
}

/** Scale that grows into place. Never starts below 0.94: nothing real appears out of nothing. */
export function growIn(frame: number, start: number, span: number, from = 0.985): number {
  return interpolate(frame, [start, start + span], [from, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: easeOut,
  })
}

/** 0 to 1 across `span` frames, for a bar filling or a number counting. */
export function progress(frame: number, start: number, span: number): number {
  return interpolate(frame, [start, start + span], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: easeOut,
  })
}
