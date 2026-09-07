#!/usr/bin/env node
// A tiny stand-in for the real sidecar, used only by sidecar-process tests.
// It speaks the same handshake: READY <port> on stdout, then /health.
import http from 'node:http'
import { existsSync, writeFileSync } from 'node:fs'

function readArg(name) {
  const index = process.argv.indexOf(name)
  return index === -1 ? undefined : process.argv[index + 1]
}

const requestedPort = Number(readArg('--port') ?? '0')
const token = readArg('--token') ?? ''

const crashOnceMarker = process.env.FAKE_SIDECAR_CRASH_ONCE_MARKER
if (crashOnceMarker && !existsSync(crashOnceMarker)) {
  writeFileSync(crashOnceMarker, '1')
  process.stderr.write('fake sidecar: simulated one-time startup failure\n')
  process.exit(1)
}

if (process.env.FAKE_SIDECAR_FAIL === '1') {
  process.stderr.write('fake sidecar: simulated startup failure\n')
  process.exit(1)
}

const server = http.createServer((request, response) => {
  if (request.url === '/health') {
    const authorized = request.headers.authorization === `Bearer ${token}`
    response.writeHead(200, { 'content-type': 'application/json' })
    response.end(JSON.stringify({ status: 'ok', authorized }))
    return
  }
  response.writeHead(404)
  response.end()
})

server.listen(requestedPort, '127.0.0.1', () => {
  const address = server.address()
  const port = typeof address === 'object' && address ? address.port : requestedPort
  const readyDelayMs = Number(process.env.FAKE_SIDECAR_READY_DELAY_MS ?? '0')
  setTimeout(() => {
    process.stdout.write(`READY ${port}\n`)
  }, readyDelayMs)
})

const crashAfterMs = process.env.FAKE_SIDECAR_CRASH_AFTER_MS
if (crashAfterMs) {
  setTimeout(() => process.exit(1), Number(crashAfterMs))
}

if (process.env.FAKE_SIDECAR_IGNORE_SIGTERM === '1') {
  // A no-op listener, not the absence of one: Node's default SIGTERM
  // disposition is to terminate, which would defeat the point of this flag.
  process.on('SIGTERM', () => {})
} else {
  process.on('SIGTERM', () => server.close(() => process.exit(0)))
}
