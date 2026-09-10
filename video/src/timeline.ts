import clips from './clips.json'
import { FPS } from './theme'

/** Seconds into a clip, as a frame count. The clips are constant 30 fps, so this is exact. */
export const at = (seconds: number): number => Math.round(seconds * FPS)

export interface Segment {
  clip: keyof typeof clips.frames
  /** First clip frame shown. */
  trimBefore: number
  /** Clip frame after the last one shown. Defaults to the end of the clip. */
  trimAfter?: number
}

export interface CaptionSpec {
  text: string
  /** Frames into the beat. */
  from: number
  /** Frames the line stays. Defaults to the rest of the beat. */
  duration?: number
}

export interface Beat {
  name: string
  segments: Segment[]
  captions: CaptionSpec[]
}

export function segmentLength(segment: Segment): number {
  const end = segment.trimAfter ?? clips.frames[segment.clip]
  return end - segment.trimBefore
}

export function beatLength(beat: Beat): number {
  return beat.segments.reduce((total, segment) => total + segmentLength(segment), 0)
}
