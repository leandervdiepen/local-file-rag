# Comments

Uncle Bob's rules, applied everywhere: application code, config, workflow YAML, shell scripts, Makefiles.

## The rules

**Express it in code.** A comment is a failure to name something well. Before writing one, try a better function name, a named constant, or an extracted function.

**Explain why, never what.** The code says what it does. A comment earns its place by carrying the reason a reader cannot recover from the code: why this threshold, why this call order, why this workaround, why the obvious approach was rejected.

**Delete bad code, do not annotate it.** A comment apologizing for code is a rewrite that did not happen.

**Kill noise.** Never restate what a name already says. `# increment counter` above `counter += 1` costs a line and teaches the reader to skip comments.

**A comment that goes stale when the code changes is a defect.** If it names a line number, a variable it does not own, or a sequence of steps, it will rot. Invariants do not rot. Prefer them.

**A file-level block over six lines is usually three comments, two of which are history.** Git has the history.

## What this looks like here

A module docstring says what the module is for and what a reader must know to use it correctly. It does not list the functions inside.

A use case docstring states the invariant it guarantees, not its steps. Steps drift, invariants do not.

A port docstring is the whole contract, so it says what the implementation returns when the thing is missing, what it raises, whether it is idempotent, and whether it may block. That is not noise, it is the specification an adapter author works from.

A workaround names the library and version that needed it, so the next person knows when to try removing it.

A magic number becomes a named constant. If the name is not enough, the comment explains where the number came from, ideally a measurement with a date.

## Examples from this repo

Good, because the reason is unrecoverable from the code:

```python
# transformers renamed torch_dtype to dtype. Passing the old name is silently
# ignored, which loads fp32 weights and doubles resident memory.
DTYPES = {"float32": torch.float32, ...}
```

```make
# --directory, not --project: --project points uv at the environment but leaves
# the working directory at the repo root, so every relative path below breaks.
UV := uv --directory $(SIDECAR)
```

Bad, and deleted on sight:

```python
# Loop over the pages
for page in pages:
```

```python
# Returns the file id
def file_id(path: Path) -> str:
```

## Sweeping

When a file is touched, its comments are held to this standard, including comments nobody in this session wrote.
A comment that survives a sweep is one somebody would miss.
