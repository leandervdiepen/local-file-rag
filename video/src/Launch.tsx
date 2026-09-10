import { AbsoluteFill, Sequence } from 'remotion'
import { Caption } from './Caption'
import { EndCard } from './EndCard'
import { Footage } from './Footage'
import { fontsReady } from './fonts'
import { NumbersCard } from './NumbersCard'
import { color } from './theme'
import { at, beatLength, segmentLength, type Beat } from './timeline'
import { TitleCard } from './TitleCard'

void fontsReady

/**
 * Four beats cut from the four clips, then the numbers and where to get it.
 *
 * Trim points are clip seconds chosen by looking at the footage, so a new
 * take means checking every one of them against a contact sheet. A caption
 * that describes something the frame is not showing is the failure mode here,
 * and it is invisible until someone watches the render.
 */
const BEATS: Beat[] = [
  {
    name: 'search',
    segments: [{ clip: 'search', trimBefore: at(0.4), trimAfter: at(13.4) }],
    captions: [
      { text: 'Type what you remember seeing.', from: 0, duration: at(3.2) },
      { text: 'The file is called IMG_4821.png.', from: at(3.4), duration: at(3.6) },
      { text: 'Red is where your words matched.', from: at(7.2), duration: at(3.2) },
      { text: 'Or follow a single word.', from: at(10.6) },
    ],
  },
  {
    name: 'visual',
    segments: [{ clip: 'visual', trimBefore: at(0.4), trimAfter: at(14.4) }],
    captions: [
      { text: 'This time none of these words are on the page.', from: 0, duration: at(9.4) },
      { text: 'It looks at the picture, so it finds it anyway.', from: at(9.6) },
    ],
  },
  {
    // The middle of this take is nineteen seconds of waiting for a free
    // model's first token, so it is cut out and the caption over the cut says
    // how long it was. Hiding the wait would be faking a latency.
    name: 'ask',
    segments: [
      { clip: 'ask', trimBefore: at(0.4), trimAfter: at(6.6) },
      { clip: 'ask', trimBefore: at(26.4), trimAfter: at(36.4) },
    ],
    captions: [
      { text: 'Shift and Enter asks a question instead.', from: 0, duration: at(6.0) },
      { text: 'Fifteen seconds later, on a free model.', from: at(6.2), duration: at(3.4) },
      { text: 'The answer links to the pages it used.', from: at(9.8), duration: at(3.4) },
      { text: 'Run Ollama and this never leaves your Mac.', from: at(13.4) },
    ],
  },
  {
    name: 'index',
    segments: [{ clip: 'index', trimBefore: at(0.9), trimAfter: at(7.2) }],
    captions: [
      { text: 'It also shows every file it skipped, and why.', from: 0, duration: at(3.4) },
      { text: 'All of it is on your disk. None of it is anywhere else.', from: at(3.6) },
    ],
  },
]

const TITLE = at(2.6)
const NUMBERS = at(7)
const END = at(4)

const beatStarts = BEATS.reduce<number[]>((starts, beat, index) => {
  const previous = index === 0 ? TITLE : starts[index - 1] + beatLength(BEATS[index - 1])
  return [...starts, previous]
}, [])
const footageEnd = beatStarts[BEATS.length - 1] + beatLength(BEATS[BEATS.length - 1])

export const LAUNCH_FRAMES = footageEnd + NUMBERS + END

export const Launch = () => (
  <AbsoluteFill style={{ backgroundColor: color.surface }}>
    <Sequence from={0} durationInFrames={TITLE} name="Title">
      <TitleCard />
    </Sequence>

    {BEATS.map((beat, index) => {
      let offset = 0
      return (
        <Sequence key={beat.name} from={beatStarts[index]} durationInFrames={beatLength(beat)} name={beat.name}>
          {beat.segments.map((segment, segmentIndex) => {
            const from = offset
            offset += segmentLength(segment)
            return (
              <Sequence
                key={segmentIndex}
                from={from}
                durationInFrames={segmentLength(segment)}
                name={`${beat.name} ${segmentIndex + 1}`}
              >
                <Footage
                  clip={segment.clip}
                  trimBefore={segment.trimBefore}
                  trimAfter={segment.trimAfter}
                  enter={index === 0 && segmentIndex === 0}
                />
              </Sequence>
            )
          })}
          {beat.captions.map((caption) => (
            <Caption key={caption.text} from={caption.from} duration={caption.duration}>
              {caption.text}
            </Caption>
          ))}
        </Sequence>
      )
    })}

    <Sequence from={footageEnd} durationInFrames={NUMBERS} name="Measured">
      <NumbersCard />
    </Sequence>
    <Sequence from={footageEnd + NUMBERS} durationInFrames={END} name="End">
      <EndCard />
    </Sequence>
  </AbsoluteFill>
)
