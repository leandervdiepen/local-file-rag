import { OffthreadVideo, staticFile, useCurrentFrame } from 'remotion'
import { fadeIn, growIn } from './motion'
import { color, FADE, shadowControl } from './theme'

/** The recorded viewport is 1280 by 800 at a device scale factor of 2, shown here at exactly half: one source pixel pair per frame pixel. */
export const WINDOW = { width: 1280, height: 800, top: 80 }
export const WINDOW_LEFT = (1920 - WINDOW.width) / 2

interface FootageProps {
  clip: string
  /** Frames of the clip to skip before the first one shown. */
  trimBefore?: number
  /** Frame of the clip after which nothing is shown. */
  trimAfter?: number
  /** Fade the window in from the surface, for the first beat. */
  enter?: boolean
}

/**
 * The app, in a window-shaped frame: the app's own control radius and hairline
 * ring, no invented chrome. Every pixel inside the ring is the app's own work.
 */
export function Footage({ clip, trimBefore, trimAfter, enter = false }: FootageProps) {
  const frame = useCurrentFrame()
  const opacity = enter ? fadeIn(frame, 0, FADE) : 1
  // The window settles the last one and a half percent into place rather than
  // cutting in at full size. Small enough that nobody sees it happen.
  const scale = enter ? growIn(frame, 0, FADE * 2) : 1

  return (
    <div
      style={{
        position: 'absolute',
        left: WINDOW_LEFT,
        top: WINDOW.top,
        width: WINDOW.width,
        height: WINDOW.height,
        borderRadius: 12,
        overflow: 'hidden',
        boxShadow: shadowControl,
        backgroundColor: color.surface,
        opacity,
        transform: `scale(${scale})`,
      }}
    >
      <OffthreadVideo
        src={staticFile(`clips/${clip}.mp4`)}
        trimBefore={trimBefore}
        trimAfter={trimAfter}
        muted
        style={{ width: WINDOW.width, height: WINDOW.height, display: 'block' }}
      />
    </div>
  )
}
