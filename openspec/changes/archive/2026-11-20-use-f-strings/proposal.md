# Proposal

## Why

The code builds nearly every message with `str.format()`: 106 calls across the package, the release
script and the tests. Each placeholder is a short name like `{p}` or `{n}`, so you have to read to the
end of the call to see what goes in it. f-strings put the value where it's shown, and they're what
current Python code uses. Nothing in the lint rules prefers one style over the other, so new code
could keep adding `.format()` calls.

## What Changes

- Every `.format()` call in `src/rfc_qa`, `scripts` and `tests` becomes an f-string, including
  messages split across several lines.
- The two templates that are defined once and filled in later become small functions that return
  an f-string:
  - `RFC_URL_TEMPLATE` in `rfc_downloader` becomes `_rfc_url(number)`.
  - `SKILL` in the architecture-script tests becomes a function of the model name.

  Afterwards no `.format()` call remains.
- ruff's pyupgrade rules (`UP`) join the selected lint rules. They report `.format()` and `%`
  formatting that an f-string can replace, along with other syntax that the project's minimum Python
  version makes outdated. Today they find only the f-string cases. ruff is pinned, so a new pyupgrade
  rule only applies when the pin is bumped.
- Every message keeps its exact text. The f-strings use the same conversions, such as `!r`, so the
  output doesn't change. The format of a number or path in a message doesn't change either.
- **BREAKING** (internal only): `rfc_downloader.RFC_URL_TEMPLATE` is removed. Nothing outside the
  module uses it, and the project isn't deployed.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `code-quality`: the lint rules also include the linter's checks for syntax that the project's
  minimum Python version makes outdated, such as string formatting that an f-string can replace.

## Impact

- Code:
  - `src/rfc_qa/query.py`, `paths.py`, `generation/answer_generator.py`, `ingestion/ingest.py`,
    `ingestion/rfc_downloader.py`, `ingestion/chunker.py` and `retrieval/keyword_index.py`.
  - `scripts/update_architecture.py`.
  - Nine test modules.
- Configuration: `pyproject.toml` adds `UP` to `[tool.ruff.lint] select`. No tool versions or
  dependencies change.
- Behavior: none. Messages, command output and the public API stay the same, apart from the
  removed `RFC_URL_TEMPLATE` constant.
- `ARCHITECTURE.md` still mentions `RFC_URL_TEMPLATE`. It's regenerated from the code before each
  release, so this change leaves it alone.
