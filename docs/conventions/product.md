# Product

`docs/PRD.md` holds what v1 is.
This file is how to decide the things the PRD does not name, so the answer does not depend on who is asking.

## The four principles, as tiebreakers

1. **Local by default.** The index and every embedding stay on the machine. The answer step is the only network call, it is labeled, and offline mode disables it.
2. **Show the work.** Every result can explain itself. The index can be inspected and corrected.
3. **Embed lazily.** Cheap signals cover everything. Expensive vectors exist only for pages a query touched or a user recently opened.
4. **Measure inside the product.** The app reports its own recall.

When two options look equally good, the one that serves a higher principle wins.
When an option violates principle 1, it does not ship, whatever it buys.

## The demo is the spec

The 45 second demo in `docs/PRD.md` is the acceptance test for the product as a whole.

Search a screenshot by what is drawn in it.
Find a slide by what its chart shows, with no matching text on the page.
Ask a question and get an answer with a citation that opens to a heatmap.
Open the index screen and see exactly what the app knows.

Work that makes one of those four moments better outranks work that does not.
That is the whole prioritization rule, and it is why the heatmap and the index screen are on the never-cut list.

## Scope

A new file type, source or platform is out until `docs/PRD.md` says otherwise.
The answer to a good idea is `docs/STATUS.md` under `Ideas parked`, not a branch.

The cut order is decided in advance, in `docs/PLAN.md`, precisely so it is not decided at 2am on day 6 by whoever is tired.
Cutting in that order is a normal outcome, not a failure. Cutting out of order needs a written reason.

Never cut: the heatmap, the index screen, the cold page cap with progress text, the DMG.
Those four are the product. Everything else is the product being nicer.

## Honesty

The privacy claim in the README is a specification, not marketing.
"Nothing leaves the machine except the answer call" has to be literally true of the code, word for word, or the sentence changes.

Every number published anywhere comes from a run that happened, carrying machine, model and date.
A number without a measurement behind it does not go in a doc, a README or a commit message.

When the golden set says recall@5 is 0.72 and the target was 0.8, the README says 0.72 and the failing queries get written down.
A product that reports its own recall cannot round it.

## What "done" means

A feature is done when its acceptance test passes in the real app: real files, real sidecar, real Electron window.
Not when the code exists, not when the unit test is green.

Every state in the checklist in `docs/conventions/design.md` is drawn and built. A feature with an undesigned error state is not done, it is demoed.

## Naming

The working name is `local-file-rag` and it appears everywhere a name is needed.
It is a placeholder. Changing it late is cheap if nothing hardcodes it outside one constant, and expensive otherwise, so nothing hardcodes it outside one constant.
