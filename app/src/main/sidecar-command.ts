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
 * The one function that decides how to launch the sidecar.
 * Dev runs the Python source through uv from the sidecar package.
 * Production runs the PyInstaller onedir bundle electron-builder copies
 * into resourcesPath via extraResources.
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
