import { Config } from '@remotion/cli/config'

// Frames are extracted from the footage at full size and scaled once in the
// composition, so jpeg here costs nothing visible and renders a third faster.
Config.setVideoImageFormat('jpeg')
Config.setJpegQuality(92)
Config.setPixelFormat('yuv420p')
Config.setOverwriteOutput(true)
