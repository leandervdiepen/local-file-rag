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

describe('where the index lives', () => {
  it('leaves the sidecar to its default when nothing says otherwise', () => {
    const result = resolveSidecarCommand({
      isPackaged: false,
      resourcesPath: '/res',
      sidecarProjectPath: '/side',
      port: 0,
      token: 't',
    })

    expect(result.args).not.toContain('--db')
  })

  it('points the sidecar at a given database, which is how a test stays out of the real index', () => {
    const result = resolveSidecarCommand({
      isPackaged: false,
      resourcesPath: '/res',
      sidecarProjectPath: '/side',
      port: 0,
      token: 't',
      dbPath: '/tmp/somewhere/db',
    })

    expect(result.args).toEqual(expect.arrayContaining(['--db', '/tmp/somewhere/db']))
  })

  it('does the same for the packaged binary', () => {
    const result = resolveSidecarCommand({
      isPackaged: true,
      resourcesPath: '/res',
      sidecarProjectPath: '/side',
      port: 0,
      token: 't',
      dbPath: '/tmp/somewhere/db',
    })

    expect(result.args).toEqual(expect.arrayContaining(['--db', '/tmp/somewhere/db']))
  })
})
