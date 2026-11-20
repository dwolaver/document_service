# Proposal

## Why

Nothing checks code style, lint errors or types. Today the only automated check is the test suite.
Formatting depends on whoever wrote the line, so lines run from 100 to 118 characters. A mistake a
linter or type checker would catch, such as an unused import or a wrong argument type, is caught
only if a test happens to reach it. Adding the checks now, while the package is small, keeps the
one-time cleanup small too.

## What Changes

- **ruff** lints and formats the code in `rfc_qa/`, `tests/` and `scripts/`. It's configured in
  `pyproject.toml`:
  - lines of up to 110 characters, the limit that changes the fewest existing lines;
  - ruff's default lint rules, plus import sorting (`I`) and bugbear (`B`).
- **mypy** type-checks the same code at its default strictness. Unannotated functions aren't checked,
  so today's code passes after one small fix. Stricter settings can follow in a later change,
  together with annotations.
- A **pre-commit** hook runs the ruff lint, the ruff format check and mypy before each commit. The
  hooks run the tools from the project's environment, so the versions pinned in
  `requirements-dev.txt` are the only versions.
- **CI** runs the same hooks on every file as a new `quality` check, beside `test`. Skipping the hook
  with `git commit --no-verify`, or never installing it, can't get unchecked code onto `main`.
- The existing code is reformatted once, and the few lint and type findings are fixed. The suite's
  behavior doesn't change.

Out of scope: strict type checking and adding annotations, the pyupgrade and simplify lint rules
(which would rewrite the project's `str.format` calls), other pre-commit hooks such as whitespace
fixers, and an editor configuration.

## Capabilities

### New Capabilities
- `code-quality`: The lint, format and type checks the code must pass, and the pre-commit hook that
  runs them before each commit.

### Modified Capabilities
- `continuous-integration`: The automated checks also run the code quality checks, and fail when one
  of them reports a problem.

## Impact

- New files: `.pre-commit-config.yaml`.
- Changed configuration: `pyproject.toml` gains `[tool.ruff]` and `[tool.mypy]`, and
  `requirements-dev.txt` gains pinned `ruff`, `mypy`, `types-requests` and `pre-commit`.
- CI: `.github/workflows/ci.yml` gains a `quality` job. The repository owner adds it to the required
  checks for `main`.
- Code: a one-time reformat of 15 of the 25 Python files, a fix for two lint findings in the tests
  and one type annotation in the tests. No change to `rfc_qa` behavior.
- Docs: the README's "Development" section.
- No new runtime dependencies.
