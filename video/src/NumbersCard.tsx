import { AbsoluteFill, useCurrentFrame, useVideoConfig } from 'remotion'
import { fadeInOut, progress, rise } from './motion'
import { color, FADE, FLIP, font, type } from './theme'

/**
 * Three figures from docs/STATUS.md, run 20260909T165833Z over 30 golden
 * queries. The two bars are the whole point of the card: the app is perfect
 * on pages that share a word with the query and loses more than half of the
 * pages that share none, and the second case is what it exists for.
 */
const BARS = [
  { label: 'The page shares a word with your search', hit: 21, of: 21, weak: false },
  { label: 'The page shares no words at all', hit: 4, of: 9, weak: true },
]

const SPEED = '28 to 44 ms'
const PROVENANCE = 'M1 Max, colqwen2-v1.0-merged in float16, 30 golden queries, 2026-09-09'

const BAR_WIDTH = 1280
const FILL = FADE * 3

export function NumbersCard() {
  const frame = useCurrentFrame()
  const { durationInFrames } = useVideoConfig()
  const heading = fadeInOut(frame, 0, durationInFrames, FADE)

  return (
    <AbsoluteFill style={{ alignItems: 'center', justifyContent: 'center', color: color.ink }}>
      <div style={{ width: BAR_WIDTH }}>
        <p
          style={{
            margin: 0,
            fontFamily: font.sans,
            fontWeight: 400,
            color: color.inkMuted,
            opacity: heading,
            ...type.sm,
          }}
        >
          Measured
        </p>

        <div
          style={{
            display: 'flex',
            alignItems: 'baseline',
            gap: 32,
            margin: '28px 0 64px',
            opacity: fadeInOut(frame, FLIP, durationInFrames, FLIP),
            transform: `translateY(${rise(frame, FLIP, FADE * 2)}px)`,
          }}
        >
          <span
            style={{
              fontFamily: font.mono,
              fontWeight: 500,
              fontVariantNumeric: 'tabular-nums',
              ...type.display,
            }}
          >
            {SPEED}
          </span>
          <span style={{ fontFamily: font.sans, fontWeight: 400, color: color.inkMuted, ...type.base }}>
            to search 218 pages
          </span>
        </div>

        {BARS.map((bar, index) => {
          const start = FADE * 2 + index * FADE
          const opacity = fadeInOut(frame, start, durationInFrames, FLIP)
          const filled = (bar.hit / bar.of) * progress(frame, start + FLIP, FILL)
          return (
            <div key={bar.label} style={{ marginBottom: 44, opacity }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 18 }}>
                <span style={{ fontFamily: font.sans, fontWeight: 400, color: color.inkMuted, ...type.base }}>
                  {bar.label}
                </span>
                <span
                  style={{
                    fontFamily: font.mono,
                    fontWeight: 500,
                    fontVariantNumeric: 'tabular-nums',
                    color: bar.weak ? color.heat : color.ink,
                    ...type.base,
                  }}
                >
                  {bar.hit} of {bar.of}
                </span>
              </div>
              <div style={{ height: 12, borderRadius: 6, backgroundColor: color.border, overflow: 'hidden' }}>
                <div
                  style={{
                    height: '100%',
                    width: `${filled * 100}%`,
                    borderRadius: 6,
                    backgroundColor: bar.weak ? color.heat : color.ink,
                  }}
                />
              </div>
            </div>
          )
        })}

        <p
          style={{
            margin: '40px 0 0',
            fontFamily: font.mono,
            fontWeight: 400,
            color: color.inkMuted,
            opacity: fadeInOut(frame, FADE * 4, durationInFrames, FLIP),
            ...type.xs,
          }}
        >
          {PROVENANCE}
        </p>
      </div>
    </AbsoluteFill>
  )
}
