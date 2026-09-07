import path from 'node:path'

export interface SidecarCommand {
  command: string
  args: string[]
}

export interface SidecarCommandInput {
  isPackaged: boolean
  resourcesPath: string
  sidecarProjectPath: string
  port: number
  token: string
}

/**
 * The one function that knows there are two ways to start the sidecar.
 * The packaged branch points at where electron-builder's `extraResources`
 * drops the PyInstaller bundle, so the two move together or the launch breaks.
 */
export function resolveSidecarCommand(input: SidecarCommandInput): SidecarCommand {
  const handshakeArgs = ['--port', String(input.port), '--token', input.token]

  if (input.isPackaged) {
    return {
      command: path.join(input.resourcesPath, 'sidecar', 'sidecar'),
      args: handshakeArgs,
    }
  }

  return {
    command: 'uv',
    args: ['run', '--project', input.sidecarProjectPath, 'sidecar', ...handshakeArgs],
  }
}
