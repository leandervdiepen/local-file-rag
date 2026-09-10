import { AbsoluteFill, useCurrentFrame, useVideoConfig } from 'remotion'
import { fadeInOut, rise } from './motion'
import { color, FADE, FLIP, font, type } from './theme'

/** The name, and the one line that says what it is for. */
export function TitleCard() {
  const frame = useCurrentFrame()
  const { durationInFrames } = useVideoConfig()
  const title = fadeInOut(frame, 0, durationInFrames, FADE)
  const line = fadeInOut(frame, FADE, durationInFrames, FLIP)

  return (
    <AbsoluteFill style={{ alignItems: 'center', justifyContent: 'center', color: color.ink }}>
      <h1
        style={{
          margin: 0,
          fontFamily: font.sans,
          fontWeight: 500,
          opacity: title,
          transform: `translateY(${rise(frame, 0, FADE * 2, 18)}px)`,
          ...type.display,
        }}
      >
        Local file search
      </h1>
      <p
        style={{
          margin: '24px 0 0',
          maxWidth: 1200,
          textAlign: 'center',
          fontFamily: font.sans,
          fontWeight: 400,
          color: color.inkMuted,
          opacity: line,
          transform: `translateY(${rise(frame, FADE, FADE * 2, 14)}px)`,
          ...type.lg,
        }}
      >
        Find a file by describing what is on it.
      </p>
    </AbsoluteFill>
  )
}
