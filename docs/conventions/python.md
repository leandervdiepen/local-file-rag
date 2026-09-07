# Python sidecar

Python 3.12, uv, ruff for format and lint, mypy strict, pytest.
Layout is `sidecar/src/sidecar/{domain,application,infrastructure,interface}`.
The layer map and the two how-tos live in the root `AGENTS.md`. This file is the code style that makes them work.

## Domain

Standard library and numpy. Nothing else, ever.
If a domain function needs a third party import, it is not a domain function.

Entities are frozen dataclasses.
A domain object cannot be constructed in an invalid state, so validation happens in `__post_init__` and raises a domain error, not a `ValueError` with a string.

Domain functions are pure and total.
Given the same input they return the same output, they touch no clock, no disk, no random source.
A function that needs the time takes the time as an argument.

This is what makes the domain testable without a single fake, and it is why gate rules, MaxSim, the heatmap grid mapping and citation parsing all live here rather than next to the code that calls them.

## Ports

A port is a `typing.Protocol` in `application/ports.py`.
It is named for the capability it provides, not the technology behind it: `PageStore`, not `LanceDBPort`. `TextExtractor`, not `PdfiumWrapper`.

A port method speaks in domain types only.
The moment a `Protocol` signature mentions a library type, the abstraction has leaked and the adapter is no longer swappable.

Ports stay small. Five methods is a lot. A port with fifteen methods is three ports.

The `Protocol` plus its docstrings is the entire contract.
An agent implementing an adapter reads the `Protocol` and nothing else, so anything an implementer must know is written there: what it returns when the thing is missing, what it raises, whether it is idempotent, whether it may block.

## Use cases

One use case per file in `application/`, named for what it does: `index_folder.py`, `search.py`.
A use case is a class with a constructor taking its ports and one public method.

The docstring states the invariant it guarantees, not the steps it takes.
Steps drift, invariants do not, and the invariant is what a reader actually needs.

Good: "Returns pages ranked by relevance. A page is only in the result if the file still exists on disk."
Bad: "Runs FTS, then embeds candidates, then reranks."

Use cases never import from `infrastructure` and never touch `flask`.
They raise domain errors. Mapping a domain error to a status code is `interface/` work.

## Infrastructure

One adapter per file, named after the dependency it wraps.
One external dependency per file. An adapter importing both `lancedb` and `anthropic` is two adapters.

Convert at the boundary.
Everything a library hands back becomes a domain type before it leaves the file, and everything going in is converted from one.
No `dict` from LanceDB, no `PIL.Image`, no `anthropic.Message` ever appears in `application` or `domain`.

Adapters own retries, timeouts and library quirks.
A workaround for library behavior belongs in the adapter with a comment saying which version needed it.

## Concurrency

waitress serves with threads, so anything the routes touch is either immutable or guarded.

The index is written by exactly one worker thread.
Routes enqueue work and read state. Two threads never write LanceDB at once.

The model is loaded lazily behind a lock, used under that lock, and unloaded after ten idle minutes.
Loading a 2B parameter model twice because two requests raced is a bug that only shows up under demo conditions, which is the worst time.

Anything that can block for more than a moment takes a cancellation check, because the client can hang up and SSE generators must notice.

## Style

Type hints on every signature, including `-> None`. mypy runs strict and its complaints are real.

Names say what the thing is. `pages`, not `data`. `skip_reason`, not `reason`. `stage1_ms`, not `t`.

No comment that restates the code.
Comments explain why: why this threshold, why this library is called in this order, why this workaround exists.

Errors are types, not strings.
`SkipReason` is an enum, not a message. The message is generated from it at the interface, so the UI can group and count by reason.

Logging goes to stderr as one line per event with a level.
stdout belongs to the handshake: the sidecar prints `READY <port>` there and nothing else, ever.
A stray `print` in the sidecar breaks app startup, which is why nothing in `src/` calls `print`.
