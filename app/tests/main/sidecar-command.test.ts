import { describe, expect, it } from 'vitest'
import { resolveSidecarCommand } from '../../src/main/sidecar-command'

describe('resolveSidecarCommand', () => {
  it('runs the Python source through uv in development', () => {
    const result = resolveSidecarCommand({
      isPackaged: false,
      resourcesPath: '/unused',
      sidecarProjectPath: '/repo/sidecar',
      port: 0,
      token: 'abc123',
    })

    expect(result).toEqual({
      command: 'uv',
      args: ['run', '--project', '/repo/sidecar', 'sidecar', '--port', '0', '--token', 'abc123'],
    })
  })

  it('runs the packaged bundle under resourcesPath in production', () => {
    const result = resolveSidecarCommand({
      isPackaged: true,
      resourcesPath: '/Applications/App.app/Contents/Resources',
      sidecarProjectPath: '/unused',
      port: 0,
      token: 'abc123',
    })

    expect(result.command).toBe('/Applications/App.app/Contents/Resources/sidecar/sidecar')
    expect(result.args).toEqual(['--port', '0', '--token', 'abc123'])
  })
})
