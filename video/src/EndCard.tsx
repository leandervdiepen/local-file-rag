import { AbsoluteFill, useCurrentFrame } from 'remotion'
import { fadeIn, rise } from './motion'
import { color, FADE, FLIP, font, type } from './theme'

const REPO = 'github.com/leandervdiepen/local-file-rag'

/** Where to get it. This card holds to the last frame, so a paused player ends on the repo and not on black. */
export function EndCard() {
  const frame = useCurrentFrame()

  return (
    <AbsoluteFill style={{ alignItems: 'center', justifyContent: 'center', color: color.ink }}>
      <h1
        style={{
          margin: 0,
          fontFamily: font.sans,
          fontWeight: 500,
          opacity: fadeIn(frame, 0, FADE),
          transform: `translateY(${rise(frame, 0, FADE * 2, 18)}px)`,
          ...type.display,
        }}
      >
        Local file search
      </h1>
      <p
        style={{
          margin: '28px 0 0',
          fontFamily: font.sans,
          fontWeight: 400,
          color: color.inkMuted,
          opacity: fadeIn(frame, FADE, FLIP),
          transform: `translateY(${rise(frame, FADE, FADE * 2, 14)}px)`,
          ...type.lg,
        }}
      >
        Free for macOS on Apple silicon.
      </p>
      <p
        style={{
          margin: '96px 0 0',
          fontFamily: font.mono,
          fontWeight: 400,
          opacity: fadeIn(frame, FADE + FLIP, FLIP),
          transform: `translateY(${rise(frame, FADE + FLIP, FADE * 2, 10)}px)`,
          ...type.base,
        }}
      >
        {REPO}
      </p>
    </AbsoluteFill>
  )
}
