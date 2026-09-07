# Electron main and preload

Main exists to do three things the renderer cannot: own the sidecar process, talk to macOS, and hold the encrypted key.
Anything else that ends up in main is renderer code in the wrong process.

## Security posture

Non negotiable, set once in the `BrowserWindow` and never loosened for convenience:

| Setting | Value |
| --- | --- |
| `contextIsolation` | `true` |
| `nodeIntegration` | `false` |
| `sandbox` | `true` |
| `webSecurity` | `true` |

The content security policy allows `connect-src` to the sidecar origin and `'self'`, and nothing else.
No remote origin appears in any policy, because the renderer never talks to the network. Only the sidecar does, and only for the answer call.

`setWindowOpenHandler` denies every window and hands external links to `shell.openExternal` after checking the scheme is `https:`.
A file path from the index is opened with `shell.openPath`, never through a URL.

## Preload

The bridge is a typed surface and nothing else.
It exposes named functions. It never exposes `ipcRenderer`, a channel name, or anything with `send` on it.

```ts
window.bridge = {
  sidecar: { baseUrl, token },
  openPath(path), revealInFinder(path), copyPath(path),
  pickFolder(), setAnthropicKey(key), onSidecarState(cb),
}
```

Every argument that crosses the bridge is validated in main before use.
The renderer is the least trusted part of this app: it renders file content, and a path arriving at `shell.openPath` is checked against the set of indexed folders first.
A renderer bug must not become a way to open an arbitrary path.

The bridge type is declared once and imported by both sides, so a change to main that the renderer has not caught up with is a typecheck failure rather than a runtime `undefined`.

## Sidecar lifecycle

Main spawns `sidecar --port 0 --token <random>` with a token generated per launch from `crypto.randomBytes`.

The handshake is a single line on stdout: `READY <port>`.
Main reads stdout until that line, with a timeout. Anything else on stdout is a protocol violation and gets logged.
stderr is the sidecar's log and is piped to main's log, never parsed.

State is a small machine, and the renderer sees it, because "the engine is starting" is a real UI state:

`starting` to `ready`, or to `failed` with a reason.
`ready` to `crashed` when the process exits without being asked.

A crash restarts the sidecar with backoff, at most three times.
After the third, the app shows the sidecar-down state with a restart button rather than looping.
LanceDB is the only state, so a restart loses nothing. That is why the restart is safe to make automatic.

On quit main sends `SIGTERM` and waits up to five seconds for a flush, then `SIGKILL`.
Quit never hangs on a wedged sidecar.

In development the sidecar is `uv run`. In production it is the PyInstaller bundle under `process.resourcesPath`.
That branch lives in exactly one function, so nothing else in main knows there are two ways to start it.

## Secrets

The Anthropic key is stored with `safeStorage.encryptString` and written to a file in `userData`.
It is decrypted in main, sent once per launch to the sidecar over the authenticated local API, and never written anywhere else.
It never crosses the preload bridge in the readable direction. The renderer can set a key and can ask whether one exists. It can never read one back.

## Files

`main/` holds one file per concern: `window.ts`, `sidecar-process.ts`, `native-actions.ts`, `secrets.ts`, `menu.ts`.
No file in `main/` imports from `renderer/`.
The only shared code is the bridge type and pure helpers, which live where both can reach them without either owning the other.
