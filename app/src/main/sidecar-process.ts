import { spawn, type ChildProcessByStdio } from 'node:child_process'
import type { Readable } from 'node:stream'
import type { SidecarStateEvent } from '../preload/bridge-types'
import { createHandshakeScanner } from './handshake-scanner'

type SidecarChildProcess = ChildProcessByStdio<null, Readable, Readable>

export interface SidecarProcessOptions {
  command: string
  args: string[]
  cwd?: string
  env?: NodeJS.ProcessEnv
  handshakeTimeoutMs?: number
  maxRestarts?: number
  shutdownGraceMs?: number
  backoffMs?: (attempt: number) => number
  onLog?: (line: string) => void
}

function defaultBackoff(attempt: number): number {
  return Math.min(500 * 2 ** (attempt - 1), 4000)
}

/**
 * Owns the sidecar child process and the state machine the renderer renders:
 * starting -> ready | crashed | failed, ready -> crashed | failed,
 * crashed -> starting | failed. failed is terminal until restart() is called.
 */
export class SidecarProcess {
  private readonly handshakeTimeoutMs: number
  private readonly maxRestarts: number
  private readonly shutdownGraceMs: number
  private readonly backoffMs: (attempt: number) => number
  private child: SidecarChildProcess | null = null
  // Node leaves exitCode null for a process killed by a signal, so exitCode
  // alone cannot tell "still running" from "died by SIGKILL". Track it ourselves.
  private childExited = true
  private state: SidecarStateEvent = { status: 'starting' }
  private attempt = 0
  private stopping = false
  private handshakeTimer: ReturnType<typeof setTimeout> | null = null
  private backoffTimer: ReturnType<typeof setTimeout> | null = null
  private readonly listeners = new Set<(event: SidecarStateEvent) => void>()

  constructor(private readonly options: SidecarProcessOptions) {
    this.handshakeTimeoutMs = options.handshakeTimeoutMs ?? 15_000
    this.maxRestarts = options.maxRestarts ?? 3
    this.shutdownGraceMs = options.shutdownGraceMs ?? 5_000
    this.backoffMs = options.backoffMs ?? defaultBackoff
  }

  getState(): SidecarStateEvent {
    return this.state
  }

  onState(listener: (event: SidecarStateEvent) => void): () => void {
    this.listeners.add(listener)
    return () => this.listeners.delete(listener)
  }

  start(): void {
    this.stopping = false
    this.attempt = 0
    this.spawnAndHandshake()
  }

  restart(): void {
    this.clearBackoffTimer()
    this.clearHandshakeTimer()
    if (this.child && !this.childExited) {
      this.child.kill('SIGKILL')
    }
    this.attempt = 0
    this.spawnAndHandshake()
  }

  async stop(): Promise<void> {
    this.stopping = true
    this.clearHandshakeTimer()
    this.clearBackoffTimer()
    const child = this.child
    if (!child || this.childExited) return

    await new Promise<void>((resolveStop) => {
      const killTimer = setTimeout(() => child.kill('SIGKILL'), this.shutdownGraceMs)
      child.once('exit', () => {
        clearTimeout(killTimer)
        resolveStop()
      })
      child.kill('SIGTERM')
    })
  }

  private spawnAndHandshake(): void {
    this.setState({ status: 'starting' })

    const child = spawn(this.options.command, this.options.args, {
      cwd: this.options.cwd,
      env: this.options.env,
      stdio: ['ignore', 'pipe', 'pipe'],
    })
    this.child = child
    this.childExited = false

    // Guards against double-reporting the same termination (e.g. a timeout's
    // SIGKILL also triggering 'exit'). Scoped to this spawn only: reaching
    // ready must NOT block reporting a later, real crash on this same child.
    let terminationHandled = false
    const reportTermination = (reason: string): void => {
      if (terminationHandled) return
      terminationHandled = true
      this.clearHandshakeTimer()
      this.handleFailure(reason)
    }

    child.stdout.on(
      'data',
      createHandshakeScanner({
        onReady: (port) => {
          this.clearHandshakeTimer()
          this.onReady(port)
        },
        onProtocolViolation: (line) => this.options.onLog?.(line),
      }),
    )

    child.stderr.on('data', (chunk: Buffer) => {
      this.options.onLog?.(chunk.toString('utf8').trimEnd())
    })

    child.once('error', (error) => reportTermination(error.message))

    child.once('exit', (code, signal) => {
      this.childExited = true
      if (this.stopping) {
        terminationHandled = true
        return
      }
      reportTermination(`exited with code ${code ?? 'null'}, signal ${signal ?? 'null'}`)
    })

    this.handshakeTimer = setTimeout(() => {
      child.kill('SIGKILL')
      reportTermination('timed out waiting for the READY line')
    }, this.handshakeTimeoutMs)
  }

  private onReady(port: number): void {
    this.attempt = 0
    this.setState({ status: 'ready', baseUrl: `http://127.0.0.1:${port}` })
  }

  private handleFailure(reason: string): void {
    this.attempt += 1

    if (this.attempt > this.maxRestarts) {
      this.setState({ status: 'failed', reason })
      return
    }

    this.setState({ status: 'crashed', reason, attempt: this.attempt, maxAttempts: this.maxRestarts })
    this.backoffTimer = setTimeout(() => this.spawnAndHandshake(), this.backoffMs(this.attempt))
  }

  private setState(next: SidecarStateEvent): void {
    this.state = next
    for (const listener of this.listeners) listener(next)
  }

  private clearHandshakeTimer(): void {
    if (this.handshakeTimer) {
      clearTimeout(this.handshakeTimer)
      this.handshakeTimer = null
    }
  }

  private clearBackoffTimer(): void {
    if (this.backoffTimer) {
      clearTimeout(this.backoffTimer)
      this.backoffTimer = null
    }
  }
}

export function createSidecarProcess(options: SidecarProcessOptions): SidecarProcess {
  return new SidecarProcess(options)
}
