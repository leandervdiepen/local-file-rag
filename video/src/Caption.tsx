import { useCurrentFrame, useVideoConfig } from 'remotion'
import { fadeInOut, rise } from './motion'
import { color, FADE, FLIP, font, type } from './theme'
import { WINDOW } from './Footage'

interface CaptionProps {
  children: string
  /** Frames into the parent sequence at which this line appears. */
  from?: number
  /** Frames the line stays. Defaults to the rest of the sequence. */
  duration?: number
}

/**
 * One line under the window. It rises a few pixels as it arrives and leaves
 * without moving, because an exit that travels asks to be watched and the
 * viewer should be looking at the app by then.
 */
export function Caption({ children, from = 0, duration }: CaptionProps) {
  const frame = useCurrentFrame()
  const { durationInFrames } = useVideoConfig()
  const end = duration === undefined ? durationInFrames : from + duration
  const opacity = fadeInOut(frame, from, end, FLIP)
  if (frame < from || frame > end) return null

  return (
    <p
      style={{
        position: 'absolute',
        left: 0,
        right: 0,
        top: WINDOW.top + WINDOW.height,
        height: 1080 - WINDOW.top - WINDOW.height,
        margin: 0,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        textAlign: 'center',
        fontFamily: font.sans,
        fontWeight: 450,
        color: color.ink,
        opacity,
        transform: `translateY(${rise(frame, from, FADE, 10)}px)`,
        ...type.base,
      }}
    >
      {children}
    </p>
  )
}
