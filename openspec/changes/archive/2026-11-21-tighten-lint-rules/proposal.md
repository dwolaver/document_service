# Proposal

## Why

The lint selection covers errors, imports, bugbear, pyupgrade and logging. It misses several kinds
of problem that ruff can find, and the current code already has some of them:

- **Unescaped patterns:** ten `pytest.raises(match=...)` patterns use regex metacharacters without a
  raw string, and some contain an unescaped `.`. So `match="ARCHITECTURE.md"` also matches
  `ARCHITECTUREXmd`, and the test checks less than it says.
- **Long lines:** `ruff format` wraps code, but it can't split a string or a comment, and `E501` isn't
  selected. One line is 122 characters, and converting to f-strings left 13 more that had to be
  wrapped by hand.
- **Files left open:** five tests call `open(...).read()` without a `with` block.
- **Leftovers:** two `int(round(...))` calls where `round` already returns an `int`, a hand-built
  list a comprehension would state directly, and a few smaller patterns.
- **Test conventions:** 14 asserts combine two checks with `and`, so a failure doesn't say which one
  failed. Parametrize arguments are written in two different styles. One fixture's name says its
  value isn't used, when a test does use it.

## What Changes

- **New lint groups.** `pyproject.toml` adds five ruff groups to `select`:
  - `E501`: lines over the 110-character limit, including strings and comments that the formatter
    can't wrap.
  - `SIM` (flake8-simplify): code that a simpler construct can replace, such as a file opened without
    a context manager.
  - `RUF` (ruff's own rules): for example unescaped `pytest.raises` patterns, mutable class-level
    defaults, redundant casts and unused `noqa` comments.
  - `PERF` (perflint): loops that build a list a comprehension would build.
  - `PT` (flake8-pytest-style): pytest conventions, such as one check per `assert`, the same style for
    every `parametrize`, and a `pytest.raises` block that holds a single statement.
- **Fix the 57 findings.** All are fixed, not suppressed. No `noqa` and no per-file ignore is added.
  - In tests: escaped patterns, files read with `pathlib`, the mutable class attributes of the
    test fakes marked as `ClassVar`, and the remaining patterns rewritten.
  - The pytest conventions:
    - composite asserts are split;
    - parametrize names are tuples and their values lists;
    - the autouse fixture `_isolated_default_data_dir` becomes `isolated_default_data_dir`, because a
      test uses its value;
    - one `pytest.raises` block calls a helper instead of holding a `try`.
  - In the package: the two redundant `int()` casts. The one long line, in the model's system
    prompt, is split with a backslash continuation, which leaves the prompt text the same.
  - In `scripts/update_architecture.py`: one comprehension.
- **Behavior unchanged.** The prompt sent to the model, every message and every command's output
  stay the same.
- **Groups left out on purpose.** The design explains why these aren't added: `PTH`, `S`, `D`, `PL`,
  `ARG`, `TRY`/`EM`, `T20`, `INP`, `FBT` and `TC`. The groups with no findings today, such as
  `C4`, `BLE` and `ISC`, can be added later in a change of their own.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `code-quality`: the lint rules also cover lines over the length limit, code a simpler construct
  can replace, the linter's own checks, such as an unescaped test pattern, and the test framework's
  conventions.

## Impact

- Configuration: `pyproject.toml`'s `select` list and its comment. No tool versions change.
- Code:
  - `src/rfc_qa/query.py` and `src/rfc_qa/generation/answer_generator.py`: the two casts and the
    prompt line.
  - `scripts/update_architecture.py`: one loop.
  - Ten test modules and `tests/conftest.py`.
- No dependency or behavior change.
