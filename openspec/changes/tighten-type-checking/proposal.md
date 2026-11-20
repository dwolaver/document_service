# Proposal

## Why

mypy runs at its default strictness, which skips every function without annotations. Almost none of
the code is annotated, so the type check covers very little: `mypy --check-untyped-defs` already finds
five places where a value's type isn't what the code assumes. Each is guarded at runtime, so none is a
bug today, but nothing would catch the next one. The package is still small, about 100 functions, so
annotating it now costs far less than it will later.

## What Changes

- `rfc_qa/` and `scripts/` are checked with `mypy --strict`. Every function there is annotated, and a
  missing annotation fails the check.
- The tests are type-checked inside their bodies, but test functions and fixtures don't need
  annotations. Annotating the 255 tests would add about 1,000 mechanical edits and catch little.
- Values that come from outside the code, such as JSON configuration, the corpus manifest and the
  model's output, are narrowed with the checks the code already makes, so mypy can prove their types.
  `Any` stays at the point where data is parsed, and doesn't spread into the rest of the code.
- A type-check suppression (`# type: ignore`) must name the error it suppresses, and an unneeded one
  fails the check.
- The five tests that patch a name a module imported, such as `rfc_downloader.requests`, patch the
  imported module itself (`requests.get`, `os.replace`, `subprocess.run`). That's the same object, so
  the tests behave the same.
- One bug that typing found is fixed. When Ollama answers HTTP 200 with JSON that isn't an object,
  such as a list, `query()` raised an uncaught `AttributeError` instead of returning a failure
  response, as the answer-generation spec requires. It now returns `MODEL_INVALID_RESPONSE`, like the
  other unusable model output. Apart from that fix, validation messages, error codes and outputs stay
  exactly as they are.

Out of scope: annotating the tests, other type checkers, and runtime type validation libraries.

## Capabilities

### New Capabilities
<!-- None. -->

### Modified Capabilities
- `code-quality`: The type check becomes strict for the package and the release scripts, and checks
  test bodies, instead of skipping unannotated code.

## Impact

- Configuration: the `[tool.mypy]` table in `pyproject.toml`, with an override for the tests.
- Code: annotations throughout `rfc_qa/` and `scripts/update_architecture.py`, and small changes where
  narrowing needs them, for example a type guard for the existing integer check in ingestion. No
  behavior changes.
- Tests: the five patch targets above. The suite's results don't change.
- Docs: the README sentence that says mypy only checks annotated functions.
- No new dependencies.
