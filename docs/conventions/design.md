# Design

The app is an instrument, not a destination.
It opens, it answers, it gets out of the way.
Minimal and spartan: monochrome, generous air, real typography, no decorative motion.

## The color rule

Color carries meaning or it does not appear.

| Scale | Where it is allowed | Never |
|---|---|---|
| ink | text, borders, surfaces, icons, everything structural | - |
| accent | focus ring, selection, the active item, links | headings, buttons at rest, decoration |
| heat | the heatmap overlay | anything that is not a match explanation |
| status | destructive confirmation, error text, warning badges | success states, progress, emphasis |

The heat scale is the reason the product exists, so it owns color.
A screen with no heatmap on it is ink on paper plus one accent.
This is why a "success green" does not exist here: a thing that worked looks like a thing that worked, not like a green thing.

Ink is warm neutral, not pure gray.
Pure gray reads cold and cheap at large areas.

Both themes are defined as tokens on `:root`, redefined under `@media (prefers-color-scheme: dark)` and again under `[data-theme]`.
Never give a color its only definition inside a media query.

## Type

Two families, both bundled with the app.

| Family | Use |
|---|---|
| Inter Variable | every piece of interface text |
| JetBrains Mono | file paths, file names, page numbers, measured values, code |

Fonts are files in the bundle.
Nothing is fetched from a font CDN, ever.
A network request for a typeface would break the privacy claim in the README, and the README is the product.

Tabular figures on every number that sits in a column or updates in place: result counts, page numbers, milliseconds, storage, token cost.
A number that shifts width while it counts is a bug.

Scale is a ramp, not a set of one-off sizes.
Line height loosens as size drops and tightens as size grows.
Measure caps around 70 characters in prose, unbounded in a result row.

## Space

4 px base unit.
Layout rhythm on multiples of 8.
Air is the main tool: a spartan interface earns its calm from space, not from lines.

Prefer space over a border.
Reach for a border only when two regions scroll independently or when a surface must read as raised.
One divider weight in the whole app.

## Motion

Motion explains a state change or it does not exist.

Three places earn it:

1. Indexing progress. The bar moves because the work is moving.
2. Streaming answer text. Tokens arrive, so text arrives.
3. The heatmap reveal. The overlay fades in over the page so the eye sees the page first, then the reason.

Everything else is instant.
No entrance animations on lists, no hover lift, no skeleton shimmer that outlives the request it stands for.

Durations stay short: 120 ms for a state flip, 200 ms for the heatmap fade.
Easing is a standard ease-out. Springs only where a gesture is being followed, and there are no gestures here.
Everything respects `prefers-reduced-motion`, which cuts duration to zero rather than swapping in a different animation.

## Keyboard first

The product is a search box.
A hand that leaves the keyboard has lost.

| Key | Does |
|---|---|
| global shortcut | opens the window with the search box focused and selected |
| typing | always goes to the search box unless a text input has focus |
| up, down | move through results across file group boundaries |
| enter | open the selected result in its default app |
| space | toggle the page preview for the selected result |
| escape | clear the query, then close the preview, then close the window |

Focus is always visible.
The focus ring is the accent, two pixels, offset from the element so it never touches the content.
Never remove an outline without putting a better one back.

## Every state gets designed

A screen is not done until all of these have been drawn and built.

| State | The question it answers |
|---|---|
| first run | what is this and what do you want from me |
| empty | there is nothing here yet, and here is the one thing to do |
| typing | something is happening, results are coming |
| partial | stage 1 is in, stage 2 is still reading pages |
| loaded | the answer |
| no results | nothing matched, and here is why that might be |
| error | what broke, and the one action that fixes it |
| offline | what still works, said as what works |
| model downloading | how far along, and that search still works meanwhile |
| sidecar down | the engine stopped, restart it |

The partial state matters most.
Stage 1 lands in milliseconds and stage 2 takes seconds, so the app is in the partial state during the moment the user is judging it.
It shows real results immediately and says what it is still reading, by name and count.

## Copy inside the interface

Say what happens.
Never spend a line on what will not happen.

Offline mode says "Search and preview work offline. Answers need the network."
It does not say "Chat is disabled."

Skip reasons say what the file is: "Image is 48 x 48, below the 300 px minimum."
They do not say "Failed."

Sentence case everywhere, including buttons and headings.
Buttons are verbs: "Add folder", "Rescan", "Forget file".
Never "Submit", never "OK" where a real verb fits.

Full rules in `copy.md`.
