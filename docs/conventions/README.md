# Conventions

One file per domain. Read the one you are about to work in.
The root `AGENTS.md` holds the layer map, the `make` targets and the two how-tos. These go deeper.

| File | Read it before |
| --- | --- |
| `product.md` | deciding what is in, what is cut, or what a number in a doc may say |
| `design.md` | any UI work: color, type, space, motion, keyboard, the state checklist |
| `copy.md` | writing any user-visible word, in the app or outside it |
| `http-api.md` | adding or changing a route, an SSE stream or an error |
| `python.md` | any sidecar code |
| `electron.md` | anything in main or preload |
| `react.md` | anything in the renderer |
| `testing.md` | writing a test, or deciding whether something deserves one |

A convention here beats a habit from another project.
When one is wrong, change it here first and then change the code, so the next person inherits the decision rather than the exception.

These describe what is true now.
A convention that narrates how something used to work is a changelog, and git already has one.
