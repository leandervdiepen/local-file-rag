# HTTP API

The sidecar is the only thing that knows how retrieval works.
The renderer knows only this contract.
Anything the renderer has to infer about internals is a hole in the contract, not a clever shortcut.

The route table lives in `docs/ARCHITECTURE.md` and is the source of truth for what exists.
This file is how those routes behave.

## Shape

Loopback only, random port, per-launch bearer token.
Every route requires `Authorization: Bearer <token>`.
A missing or wrong token is `401` with no body detail. Do not explain the auth scheme to an unauthorized caller.

JSON in, JSON out, `snake_case` keys on the wire.
The renderer converts to its own types at the infrastructure boundary and never passes a wire object deeper than that.

Paths are plural nouns. Actions that are not CRUD are a `POST` to a verb under the noun: `POST /index/rescan`, not `POST /rescan-index`.

## Errors

One error body, everywhere:

```json
{ "error": { "code": "folder_unreadable", "message": "Downloads is not readable. Grant access in System Settings.", "detail": {} } }
```

`code` is a stable `snake_case` string the renderer switches on.
`message` is written for a person and follows `copy.md`. It says what happened and the one action that fixes it.
`detail` carries structured extras and may be empty. It is never the only place a needed fact lives.

Status codes: `400` the request is wrong, `401` no token, `404` the thing does not exist, `409` the index is busy with a conflicting job, `500` we broke.
Never `200` with an error inside it.

## Server-sent events

Streaming routes are SSE over a Flask generator.
Every event is named. There is no anonymous `data:` event in this API.

Every stream obeys the same four rules:

1. It opens with a first event fast, so the UI can leave the loading state. `/search` sends `candidates` as soon as stage 1 lands.
2. It reports progress in units the user recognizes: pages read, not percent complete.
3. It ends with exactly one terminal event, `done` or `error`. A stream that just stops is a bug.
4. It survives the client hanging up. The generator checks for a closed connection and abandons the work instead of finishing an answer nobody will read.

Event payloads are JSON objects, never bare strings, so a field can be added later without breaking the parser.

`/search` emits `candidates` then zero or more `progress` then `results` then `done`.
`/chat` emits `retrieval` then many `token` then zero or more `citation` then `done` carrying usage.

A client that reads only `results` and `done` still works.
That is the test for whether the stream is designed right.

## Long work

Indexing is a job, not a request.
`POST /index/rescan` returns immediately with a job id.
Progress is read from `GET /index/stats` or streamed. The HTTP request never holds a thread for the length of a crawl.

Only one indexing job runs at a time. A second request returns `409` with `code: "index_busy"`.

## Binary

`GET /pages/{id}/image` returns `image/png` with an ETag from the page content hash and a long `Cache-Control`.
Page images are immutable for a given page id, so the renderer may cache them forever.
Everything else is `no-store`. The index changes under you and a stale count is worse than a slow one.

## Adding a route

1. Add it to the table in `docs/ARCHITECTURE.md` first. If it does not earn a row there, it does not exist.
2. The blueprint function parses and validates, calls exactly one use case, and serializes. Nothing else.
3. Business rules never live in `interface/`. A route handler with an `if` about retrieval is a use case that has not been written yet.
4. Test it through the Flask test client with fake ports, asserting the wire shape. That test is the contract.
