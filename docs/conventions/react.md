# Renderer

React 19, TypeScript, Tailwind v4, Vite.
Four layers, dependencies inward only, enforced by `dependency-cruiser`.

## The layers, concretely

`renderer/domain/` imports nothing.
Types and pure functions: grouping results by file, thresholding a heatmap grid, keyboard navigation state, cost arithmetic, formatting a byte count.
No React import belongs here. A file in `domain/` that imports React is in the wrong folder.

This is where the logic worth testing lives, and it is tested with plain function calls and no renderer at all.

`renderer/application/` holds hooks that are use cases: `useSearch`, `useChat`, `useIndex`, `useSettings`.
A hook owns a piece of the app's behavior and depends on a port, not on `fetch`.
Ports are TypeScript interfaces in `application/ports.ts`, the same idea as the sidecar's `Protocol` classes.

`renderer/infrastructure/` implements those ports with `fetch` and `EventSource` against the sidecar, plus the preload bridge.
Wire shapes are `snake_case` and stop here. Everything leaving this layer is a domain type in `camelCase`.

`renderer/ui/` holds components in feature folders: `search/`, `preview/`, `chat/`, `index/`, `settings/`, `onboarding/`, `shared/`.
A component renders state and raises events. When a component starts making decisions, the decision moves to `domain/` and the component calls it.

## Components

A component file exports one component and is named after it.
No `index.ts`. No barrel. Import the path.

Props are the component's contract. Avoid boolean flags that accumulate: three booleans mean eight states and probably two components.
Prefer composition to configuration. A `<ResultRow>` that takes an action slot beats one that takes `showOpen`, `showReveal`, `showCopy`.

Server-shaped data arrives as props or from a hook. Components do not fetch.

Keep list rows cheap. The result list can hold hundreds of rows and rerenders on every keystroke, so a row is a small pure component and the expensive parts, thumbnails and heatmaps, are lazy and cached.

## State

Local state is the default.
Lift only when a second component genuinely needs it.
There is no global store in this app. The sidecar is the state, and the hooks are the cache in front of it.

Streaming state is a reducer, not a pile of `useState`.
A search moves through `idle`, `stage1`, `reading`, `done`, `error`, and those transitions are a pure function in `domain/` that the hook drives.
That way the partial state, the one the user judges the app by, is unit tested rather than hoped for.

Never render two sources of truth for the same fact. If the footer shows a result count, it counts the rendered list.

## Async

Every request is abortable and every search aborts the one before it.
A user typing fast must never see an older response land after a newer one. The reducer ignores events tagged with a stale query id, and the fetch is aborted anyway.

`EventSource` cannot send an `Authorization` header, so SSE goes through `fetch` with a `ReadableStream` reader and a hand-rolled event parser in `infrastructure/`.
That parser is the one piece of infrastructure with real logic, so it is unit tested against raw chunk strings, including an event split across two chunks.

Errors surface as state, never as a thrown render.
Every hook returns an error shape the UI can display, using the `code` from the API to choose the message.

## Styling

Tailwind v4 with tokens defined in one CSS file.
Colors, spacing and type come from tokens named for meaning: `--color-ink-muted`, not `--color-gray-500`.
A raw hex in a component is a bug. A raw pixel value in a component is usually one too.

The heat scale is the only palette used by the canvas overlay, and it is read from the same tokens so the overlay matches the theme.

Class strings stay readable. When a class list needs a conditional beyond a ternary, it is a variant, and variants are declared next to the component rather than assembled inline.

## Accessibility

Every interactive element is a real button or link, or has a role, a tab stop and a key handler.
The result list is a listbox with `aria-activedescendant`, so arrow keys move selection without moving focus out of the search input.
That is what lets a user type and navigate without ever leaving the box.

Live regions announce what changed: the result count after a search, the answer as it streams, the indexing progress at intervals rather than on every file.

Focus is never lost. Closing the preview returns focus to the row that opened it.

## Testing

`domain/` and `application/` are covered by vitest with fakes for ports.
A component gets a test when it holds logic a user could hit wrong: the result list keyboard behavior, the heatmap threshold slider, the citation chip mapping.
Presentation-only components are covered by the end-to-end paths, not by snapshot tests. A snapshot that changes whenever a class changes teaches people to accept diffs without reading them.
